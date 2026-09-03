from django.test import TestCase
from django.utils import timezone

from apps.core.choices import (
    EventDefinitionLifecycleRoleChoices,
    EventInstanceStatusChoices,
    SubjectLifecycleStatusChoices,
    SubjectPeriodStatusChoices,
)
from apps.study.models import EventDefinition, EventTransitionRule, Site, Study
from apps.subject.application.services.early_termination import (
    SubjectEarlyTerminationRequestService,
)
from apps.subject.infrastructure.repositories.early_termination import (
    DjangoSubjectEarlyTerminationRepository,
)
from apps.subject.models import (
    Subject,
    SubjectEnrollment,
    SubjectEventInstance,
    SubjectEventInstanceTransitionLog,
    SubjectPeriod,
    SubjectPeriodTransitionLog,
    SubjectStatusHistory,
)


class SubjectEarlyTerminationRepositoryTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.study = Study.objects.create(
            created_at=self.now,
            updated_at=self.now,
            deleted=False,
            code="ET_STUDY",
            name="Early termination study",
        )
        self.site = Site.objects.create(
            created_at=self.now,
            updated_at=self.now,
            deleted=False,
            study=self.study,
            code="SITE01",
            name="Site 01",
        )
        self.subject = Subject.objects.create(
            created_at=self.now,
            updated_at=self.now,
            deleted=False,
            study=self.study,
            site=self.site,
            subject_code="SUBJ-ET-001",
            screening_code="SCR-ET-001",
            current_sequence=1,
        )
        self.enrollment = SubjectEnrollment.objects.create(
            created_at=self.now,
            updated_at=self.now,
            deleted=False,
            subject=self.subject,
            study=self.study,
            site=self.site,
            status="Enrolled",
            status_datetime=self.now,
            is_enrolled=True,
            enrollment_date=self.now.date(),
        )
        self.regular_definition = self._create_event_definition(
            code="VISIT_1",
            category="treatment",
            timing_mode="scheduled",
            lifecycle_role=EventDefinitionLifecycleRoleChoices.REGULAR,
            sequence_no=10,
        )
        self.early_termination_definition = self._create_event_definition(
            code="FU_ET",
            category="eos",
            timing_mode="conditional",
            lifecycle_role=EventDefinitionLifecycleRoleChoices.EARLY_TERMINATION,
            sequence_no=99,
        )
        self.regular_event = self._create_event_instance(
            definition=self.regular_definition,
            status=EventInstanceStatusChoices.OPEN,
        )
        self.early_termination_event = self._create_event_instance(
            definition=self.early_termination_definition,
            status=EventInstanceStatusChoices.NOT_READY,
        )
        self.repository = DjangoSubjectEarlyTerminationRepository()

    def test_capture_is_blocked_until_early_termination_is_started(self):
        regular = self.repository.get_capture_eligibility(
            subject_id=self.subject.pk,
            event_instance_id=self.regular_event.pk,
        )
        early_termination = self.repository.get_capture_eligibility(
            subject_id=self.subject.pk,
            event_instance_id=self.early_termination_event.pk,
        )

        self.assertTrue(regular.allowed)
        self.assertFalse(early_termination.allowed)
        self.assertEqual(
            early_termination.reason,
            "early_termination_not_started",
        )

        Subject.objects.filter(pk=self.subject.pk).update(
            lifecycle_status=(
                SubjectLifecycleStatusChoices.EARLY_TERMINATION_IN_PROGRESS
            )
        )

        regular = self.repository.get_capture_eligibility(
            subject_id=self.subject.pk,
            event_instance_id=self.regular_event.pk,
        )
        early_termination = self.repository.get_capture_eligibility(
            subject_id=self.subject.pk,
            event_instance_id=self.early_termination_event.pk,
        )

        self.assertFalse(regular.allowed)
        self.assertTrue(early_termination.allowed)

    def test_request_service_runs_atomic_lifecycle_with_real_transition_policy(self):
        EventTransitionRule.objects.create(
            created_at=self.now,
            updated_at=self.now,
            deleted=False,
            study=self.study,
            study_version="v1.0",
            from_event_definition=self.regular_definition,
            to_event_definition=self.early_termination_definition,
            transition_type="conditional",
            condition_scope="subject",
            condition_code="early_termination.requested",
            auto_open=True,
            auto_create=False,
            requires_previous_completion=False,
        )

        result = SubjectEarlyTerminationRequestService().request(
            study_id=self.study.pk,
            subject_id=self.subject.pk,
            actor_user_id=77,
            effective_at=self.now,
            reason_code="subject_withdrawal",
            reason_text="Subject withdrew consent.",
        )

        self.assertTrue(result.requested)
        self.subject.refresh_from_db()
        self.regular_event.refresh_from_db()
        self.early_termination_event.refresh_from_db()
        self.assertEqual(
            self.subject.lifecycle_status,
            SubjectLifecycleStatusChoices.EARLY_TERMINATION_IN_PROGRESS,
        )
        self.assertEqual(
            self.regular_event.status,
            EventInstanceStatusChoices.CANCELLED,
        )
        self.assertEqual(
            self.early_termination_event.status,
            EventInstanceStatusChoices.OPEN,
        )

    def test_request_service_rejects_subject_before_enrollment(self):
        EventTransitionRule.objects.create(
            created_at=self.now,
            updated_at=self.now,
            deleted=False,
            study=self.study,
            study_version="v1.0",
            from_event_definition=self.regular_definition,
            to_event_definition=self.early_termination_definition,
            transition_type="conditional",
            condition_scope="subject",
            condition_code="early_termination.requested",
            auto_open=True,
            auto_create=False,
            requires_previous_completion=False,
        )
        SubjectEnrollment.objects.filter(pk=self.enrollment.pk).update(
            status="Screened",
            is_enrolled=False,
            enrollment_date=None,
        )

        result = SubjectEarlyTerminationRequestService().request(
            study_id=self.study.pk,
            subject_id=self.subject.pk,
            actor_user_id=77,
            effective_at=self.now,
            reason_code="subject_withdrawal",
            reason_text="Withdrew during screening.",
        )

        self.assertFalse(result.requested)
        self.assertEqual(result.reason, "subject_not_enrolled")
        self.subject.refresh_from_db()
        self.regular_event.refresh_from_db()
        self.early_termination_event.refresh_from_db()
        self.assertEqual(
            self.subject.lifecycle_status,
            SubjectLifecycleStatusChoices.ACTIVE,
        )
        self.assertEqual(self.regular_event.status, EventInstanceStatusChoices.OPEN)
        self.assertEqual(
            self.early_termination_event.status,
            EventInstanceStatusChoices.NOT_READY,
        )

    def test_availability_excludes_subject_before_enrollment(self):
        EventTransitionRule.objects.create(
            created_at=self.now,
            updated_at=self.now,
            deleted=False,
            study=self.study,
            study_version="v1.0",
            from_event_definition=self.regular_definition,
            to_event_definition=self.early_termination_definition,
            transition_type="conditional",
            condition_scope="subject",
            condition_code="early_termination.requested",
            auto_open=True,
            auto_create=False,
            requires_previous_completion=False,
        )

        eligible_subject_ids = self.repository.list_eligible_subject_ids(
            study_id=self.study.pk,
            subject_ids=(self.subject.pk,),
        )
        self.assertEqual(eligible_subject_ids, frozenset({self.subject.pk}))

        SubjectEnrollment.objects.filter(pk=self.enrollment.pk).update(
            status="Screened",
            is_enrolled=False,
            enrollment_date=None,
        )

        eligible_subject_ids = self.repository.list_eligible_subject_ids(
            study_id=self.study.pk,
            subject_ids=(self.subject.pk,),
        )
        self.assertEqual(eligible_subject_ids, frozenset())

    def test_start_closes_other_visits_and_records_all_audit_logs(self):
        future_definition = self._create_event_definition(
            code="VISIT_2",
            category="treatment",
            timing_mode="scheduled",
            lifecycle_role=EventDefinitionLifecycleRoleChoices.REGULAR,
            sequence_no=20,
        )
        future_event = self._create_event_instance(
            definition=future_definition,
            status=EventInstanceStatusChoices.PLANNED,
        )
        period = SubjectPeriod.objects.create(
            created_at=self.now,
            updated_at=self.now,
            deleted=False,
            subject=self.subject,
            period_no=1,
            treatment_code="TREATMENT_A",
            status=SubjectPeriodStatusChoices.ACTIVE,
        )

        started = self.repository.start_early_termination(
            subject_id=self.subject.pk,
            effective_at=self.now,
            reason_code="subject_withdrawal",
            reason_text="Subject withdrew consent.",
            actor_user_id=77,
            now=self.now,
        )
        skipped_count, cancelled_count = (
            self.repository.close_other_event_instances(
                subject_id=self.subject.pk,
                early_termination_event_instance_id=(
                    self.early_termination_event.pk
                ),
                actor_user_id=77,
                now=self.now,
            )
        )
        cancelled_period_count = self.repository.cancel_open_subject_periods(
            subject_id=self.subject.pk,
            actor_user_id=77,
            now=self.now,
        )

        self.assertTrue(started)
        self.assertEqual((skipped_count, cancelled_count), (1, 1))
        self.assertEqual(cancelled_period_count, 1)
        self.subject.refresh_from_db()
        self.regular_event.refresh_from_db()
        future_event.refresh_from_db()
        period.refresh_from_db()
        self.assertEqual(
            self.subject.lifecycle_status,
            SubjectLifecycleStatusChoices.EARLY_TERMINATION_IN_PROGRESS,
        )
        self.assertEqual(
            self.regular_event.status,
            EventInstanceStatusChoices.CANCELLED,
        )
        self.assertEqual(
            future_event.status,
            EventInstanceStatusChoices.SKIPPED,
        )
        self.assertEqual(period.status, SubjectPeriodStatusChoices.CANCELLED)
        self.assertEqual(
            SubjectEventInstanceTransitionLog.objects.filter(
                subject=self.subject,
                trigger_source="early_termination",
            ).count(),
            2,
        )
        self.assertTrue(
            SubjectStatusHistory.objects.filter(
                subject=self.subject,
                from_status=SubjectLifecycleStatusChoices.ACTIVE,
                to_status=(
                    SubjectLifecycleStatusChoices.EARLY_TERMINATION_IN_PROGRESS
                ),
            ).exists()
        )
        self.assertTrue(
            SubjectPeriodTransitionLog.objects.filter(
                period=period,
                to_status=SubjectPeriodStatusChoices.CANCELLED,
            ).exists()
        )

    def test_close_other_events_preserves_completed_lifecycle_events(self):
        preserved_statuses = (
            EventInstanceStatusChoices.COMPLETED,
            EventInstanceStatusChoices.VERIFIED,
            EventInstanceStatusChoices.LOCKED,
            EventInstanceStatusChoices.FINALIZED,
        )
        SubjectEventInstance.objects.filter(pk=self.regular_event.pk).update(
            status=preserved_statuses[0],
        )
        preserved_events = [self.regular_event]
        for sequence_no, status in enumerate(preserved_statuses[1:], start=20):
            definition = self._create_event_definition(
                code=f"VISIT_{sequence_no}",
                category="treatment",
                timing_mode="scheduled",
                lifecycle_role=EventDefinitionLifecycleRoleChoices.REGULAR,
                sequence_no=sequence_no,
            )
            preserved_events.append(
                self._create_event_instance(
                    definition=definition,
                    status=status,
                )
            )

        skipped_count, cancelled_count = self.repository.close_other_event_instances(
            subject_id=self.subject.pk,
            early_termination_event_instance_id=self.early_termination_event.pk,
            actor_user_id=77,
            now=self.now,
        )

        self.assertEqual((skipped_count, cancelled_count), (0, 0))
        for event_instance, expected_status in zip(
            preserved_events,
            preserved_statuses,
            strict=True,
        ):
            event_instance.refresh_from_db()
            self.assertEqual(event_instance.status, expected_status)
        self.assertFalse(
            SubjectEventInstanceTransitionLog.objects.filter(
                subject=self.subject,
                trigger_source="early_termination",
            ).exists()
        )

    def test_completed_early_termination_event_terminates_subject_idempotently(self):
        Subject.objects.filter(pk=self.subject.pk).update(
            lifecycle_status=(
                SubjectLifecycleStatusChoices.EARLY_TERMINATION_IN_PROGRESS
            ),
            lifecycle_reason_code="other",
            lifecycle_reason_text="Clinical decision.",
        )
        SubjectEventInstance.objects.filter(
            pk=self.early_termination_event.pk
        ).update(status=EventInstanceStatusChoices.COMPLETED)

        first = self.repository.complete_subject_if_early_termination_event(
            event_instance_id=self.early_termination_event.pk,
            actor_user_id=77,
            now=self.now,
        )
        second = self.repository.complete_subject_if_early_termination_event(
            event_instance_id=self.early_termination_event.pk,
            actor_user_id=77,
            now=self.now,
        )

        self.assertTrue(first)
        self.assertFalse(second)
        self.subject.refresh_from_db()
        self.assertEqual(
            self.subject.lifecycle_status,
            SubjectLifecycleStatusChoices.EARLY_TERMINATED,
        )
        self.assertEqual(
            SubjectStatusHistory.objects.filter(
                subject=self.subject,
                to_status=SubjectLifecycleStatusChoices.EARLY_TERMINATED,
            ).count(),
            1,
        )

    def test_reopened_early_termination_event_reopens_subject_idempotently(self):
        Subject.objects.filter(pk=self.subject.pk).update(
            lifecycle_status=SubjectLifecycleStatusChoices.EARLY_TERMINATED,
            lifecycle_reason_code="other",
            lifecycle_reason_text="Clinical decision.",
        )
        SubjectEventInstance.objects.filter(
            pk=self.early_termination_event.pk
        ).update(status=EventInstanceStatusChoices.IN_PROGRESS)

        first = self.repository.reopen_subject_if_early_termination_event(
            event_instance_id=self.early_termination_event.pk,
            actor_user_id=77,
            now=self.now,
        )
        second = self.repository.reopen_subject_if_early_termination_event(
            event_instance_id=self.early_termination_event.pk,
            actor_user_id=77,
            now=self.now,
        )

        self.assertTrue(first)
        self.assertFalse(second)
        self.subject.refresh_from_db()
        self.assertEqual(
            self.subject.lifecycle_status,
            SubjectLifecycleStatusChoices.EARLY_TERMINATION_IN_PROGRESS,
        )
        self.assertEqual(
            SubjectStatusHistory.objects.filter(
                subject=self.subject,
                from_status=SubjectLifecycleStatusChoices.EARLY_TERMINATED,
                to_status=(
                    SubjectLifecycleStatusChoices.EARLY_TERMINATION_IN_PROGRESS
                ),
            ).count(),
            1,
        )

    def test_transition_context_requires_semantic_early_termination_metadata(self):
        EventTransitionRule.objects.create(
            created_at=self.now,
            updated_at=self.now,
            deleted=False,
            study=self.study,
            study_version="v1.0",
            from_event_definition=self.regular_definition,
            to_event_definition=self.early_termination_definition,
            condition_code="early_termination.requested",
            auto_open=True,
            requires_previous_completion=False,
        )

        context = self.repository.get_early_termination_transition_context(
            study_id=self.study.pk,
            subject_id=self.subject.pk,
        )

        self.assertIsNotNone(context)
        self.assertEqual(
            context.target_event_instance_id,
            self.early_termination_event.pk,
        )

        EventDefinition.objects.filter(
            pk=self.early_termination_definition.pk
        ).update(lifecycle_role=EventDefinitionLifecycleRoleChoices.REGULAR)

        context = self.repository.get_early_termination_transition_context(
            study_id=self.study.pk,
            subject_id=self.subject.pk,
        )

        self.assertIsNone(context)

    def test_open_regular_eos_is_available_but_not_treated_as_started(self):
        regular_eos_definition = self._create_event_definition(
            code="EOS",
            category="eos",
            timing_mode="scheduled",
            lifecycle_role=(
                EventDefinitionLifecycleRoleChoices.REGULAR_COMPLETION
            ),
            sequence_no=90,
        )
        regular_eos = self._create_event_instance(
            definition=regular_eos_definition,
            status=EventInstanceStatusChoices.OPEN,
        )

        reached = self.repository.get_reached_regular_eos_event_instance(
            study_id=self.study.pk,
            subject_id=self.subject.pk,
        )

        self.assertIsNone(reached)

        regular_eos.status = EventInstanceStatusChoices.IN_PROGRESS
        regular_eos.save(update_fields=["status"])

        reached = self.repository.get_reached_regular_eos_event_instance(
            study_id=self.study.pk,
            subject_id=self.subject.pk,
        )

        self.assertEqual(reached.pk, regular_eos.pk)

    def _create_event_definition(
        self,
        *,
        code,
        category,
        timing_mode,
        lifecycle_role,
        sequence_no,
    ):
        return EventDefinition.objects.create(
            created_at=self.now,
            updated_at=self.now,
            deleted=False,
            study=self.study,
            study_version="v1.0",
            code=code,
            name=code,
            event_type="visit_based",
            event_category=category,
            timing_mode=timing_mode,
            lifecycle_role=lifecycle_role,
            sequence_no=sequence_no,
            is_enabled=True,
        )

    def _create_event_instance(self, *, definition, status):
        return SubjectEventInstance.objects.create(
            created_at=self.now,
            updated_at=self.now,
            deleted=False,
            study=self.study,
            subject=self.subject,
            event_definition=definition,
            study_version="v1.0",
            status=status,
            event_code_snapshot=definition.code,
            event_name_snapshot=definition.name,
            event_type_snapshot=definition.event_type,
        )
