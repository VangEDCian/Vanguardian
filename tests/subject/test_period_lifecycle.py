from dataclasses import replace
from datetime import datetime, timezone

from django.test import SimpleTestCase, TestCase

from apps.study.models import EventDefinition, Site, Study
from apps.subject.application.services.period_lifecycle import (
    SubjectPeriodLifecycleService,
)
from apps.subject.application.services.period_override import (
    SubjectPeriodOverrideService,
)
from apps.subject.domain import (
    SubjectPeriodStatus,
    SubjectPeriodTransitionPolicy,
)
from apps.subject.infrastructure.repositories.period_lifecycle import (
    DjangoSubjectPeriodLifecycleRepository,
    SubjectPeriodEventContext,
    SubjectPeriodState,
)
from apps.subject.models import (
    Subject,
    SubjectEventInstance,
    SubjectPeriod,
    SubjectPeriodMilestone,
    SubjectPeriodTransitionLog,
    SubjectPeriodTransitionOverride,
)


class SubjectPeriodTransitionPolicyTests(SimpleTestCase):
    def setUp(self):
        self.policy = SubjectPeriodTransitionPolicy()

    def test_end_verified_enters_washout_when_required(self):
        decision = self.policy.complete_treatment(
            current_status=SubjectPeriodStatus.ACTIVE,
            has_next_period=True,
            requires_washout=True,
        )

        self.assertEqual(decision.current_status, SubjectPeriodStatus.WASHOUT)
        self.assertIsNone(decision.next_status)

    def test_end_verified_activates_next_period_without_washout(self):
        decision = self.policy.complete_treatment(
            current_status=SubjectPeriodStatus.ACTIVE,
            has_next_period=True,
            requires_washout=False,
        )

        self.assertEqual(decision.current_status, SubjectPeriodStatus.COMPLETED)
        self.assertEqual(decision.next_status, SubjectPeriodStatus.ACTIVE)

    def test_reopen_requires_review_after_next_period_started(self):
        decision = self.policy.reopen_period_end(
            current_status=SubjectPeriodStatus.COMPLETED,
            next_status=SubjectPeriodStatus.ACTIVE,
        )

        self.assertEqual(
            decision.current_status,
            SubjectPeriodStatus.REVIEW_REQUIRED,
        )

    def test_manual_override_advances_active_period_to_planned_period(self):
        decision = self.policy.override_advance_to_next_period(
            current_status=SubjectPeriodStatus.ACTIVE,
            next_status=SubjectPeriodStatus.PLANNED,
        )

        self.assertEqual(decision.current_status, SubjectPeriodStatus.COMPLETED)
        self.assertEqual(decision.next_status, SubjectPeriodStatus.ACTIVE)


class SubjectPeriodLifecycleServiceTests(SimpleTestCase):
    def test_randomization_activates_only_first_period(self):
        repository = _PeriodLifecycleRepositoryStub()
        service = SubjectPeriodLifecycleService(repository=repository)

        result = SubjectPeriodLifecycleService.initialize_after_randomization.__wrapped__(
            service,
            subject_id=20,
            actor_user_id=99,
        )

        self.assertTrue(result.has_changes)
        self.assertEqual(repository.periods[0].status, SubjectPeriodStatus.ACTIVE)
        self.assertEqual(repository.periods[1].status, SubjectPeriodStatus.PLANNED)

    def test_verified_end_event_enters_washout_and_is_idempotent(self):
        repository = _PeriodLifecycleRepositoryStub(
            periods=[
                _period(
                    period_id=1,
                    period_no=1,
                    status=SubjectPeriodStatus.ACTIVE,
                    end_event_instance_id=81,
                    washout_days=28,
                    transition_rule_code="after_washout",
                ),
                _period(period_id=2, period_no=2),
            ],
            event=_event(event_instance_id=81, status="verified"),
        )
        service = SubjectPeriodLifecycleService(repository=repository)

        first = SubjectPeriodLifecycleService.handle_event_status_changed.__wrapped__(
            service,
            event_instance_id=81,
            actor_user_id=99,
        )
        second = SubjectPeriodLifecycleService.handle_event_status_changed.__wrapped__(
            service,
            event_instance_id=81,
            actor_user_id=99,
        )

        self.assertTrue(first.has_changes)
        self.assertFalse(second.has_changes)
        self.assertEqual(repository.periods[0].status, SubjectPeriodStatus.WASHOUT)
        self.assertEqual(repository.periods[1].status, SubjectPeriodStatus.PLANNED)
        self.assertEqual(repository.period_end_records, [1])

    def test_completed_end_event_does_not_advance_period(self):
        repository = _PeriodLifecycleRepositoryStub(
            periods=[
                _period(
                    period_id=1,
                    period_no=1,
                    status=SubjectPeriodStatus.ACTIVE,
                    end_event_instance_id=81,
                ),
                _period(period_id=2, period_no=2),
            ],
            event=_event(event_instance_id=81, status="completed"),
        )
        service = SubjectPeriodLifecycleService(repository=repository)

        result = SubjectPeriodLifecycleService.handle_event_status_changed.__wrapped__(
            service,
            event_instance_id=81,
        )

        self.assertFalse(result.has_changes)
        self.assertEqual(repository.periods[0].status, SubjectPeriodStatus.ACTIVE)

    def test_verified_washout_event_activates_next_period(self):
        repository = _PeriodLifecycleRepositoryStub(
            periods=[
                _period(
                    period_id=1,
                    period_no=1,
                    status=SubjectPeriodStatus.WASHOUT,
                ),
                _period(period_id=2, period_no=2),
            ],
            event=_event(
                event_instance_id=90,
                status="verified",
                event_category="washout",
            ),
        )
        service = SubjectPeriodLifecycleService(repository=repository)

        result = SubjectPeriodLifecycleService.handle_event_status_changed.__wrapped__(
            service,
            event_instance_id=90,
            actor_user_id=99,
        )

        self.assertTrue(result.has_changes)
        self.assertEqual(repository.periods[0].status, SubjectPeriodStatus.COMPLETED)
        self.assertEqual(repository.periods[1].status, SubjectPeriodStatus.ACTIVE)
        self.assertEqual(repository.period_start_records, [2])

    def test_washout_event_before_due_date_does_not_activate_next_period(self):
        repository = _PeriodLifecycleRepositoryStub(
            periods=[
                _period(
                    period_id=1,
                    period_no=1,
                    status=SubjectPeriodStatus.WASHOUT,
                ),
                _period(period_id=2, period_no=2),
            ],
            event=_event(
                event_instance_id=90,
                status="verified",
                event_category="washout",
            ),
            washout_due=False,
        )
        service = SubjectPeriodLifecycleService(repository=repository)

        result = SubjectPeriodLifecycleService.handle_event_status_changed.__wrapped__(
            service,
            event_instance_id=90,
            actor_user_id=99,
        )

        self.assertFalse(result.has_changes)
        self.assertEqual(repository.periods[0].status, SubjectPeriodStatus.WASHOUT)
        self.assertEqual(repository.periods[1].status, SubjectPeriodStatus.PLANNED)

    def test_reopen_before_next_period_starts_restores_active_period(self):
        repository = _PeriodLifecycleRepositoryStub(
            periods=[
                _period(
                    period_id=1,
                    period_no=1,
                    status=SubjectPeriodStatus.WASHOUT,
                    end_event_instance_id=81,
                ),
                _period(period_id=2, period_no=2),
            ],
            event=_event(event_instance_id=81, status="in_progress"),
        )
        service = SubjectPeriodLifecycleService(repository=repository)

        result = SubjectPeriodLifecycleService.handle_event_status_changed.__wrapped__(
            service,
            event_instance_id=81,
            actor_user_id=99,
            trigger_source="subject_event_reopened",
        )

        self.assertTrue(result.has_changes)
        self.assertEqual(repository.periods[0].status, SubjectPeriodStatus.ACTIVE)
        self.assertEqual(repository.corrected_period_ends, [1])

    def test_reopen_after_next_period_started_requires_review(self):
        repository = _PeriodLifecycleRepositoryStub(
            periods=[
                _period(
                    period_id=1,
                    period_no=1,
                    status=SubjectPeriodStatus.COMPLETED,
                    end_event_instance_id=81,
                ),
                _period(
                    period_id=2,
                    period_no=2,
                    status=SubjectPeriodStatus.ACTIVE,
                ),
            ],
            event=_event(event_instance_id=81, status="in_progress"),
        )
        service = SubjectPeriodLifecycleService(repository=repository)

        SubjectPeriodLifecycleService.handle_event_status_changed.__wrapped__(
            service,
            event_instance_id=81,
            actor_user_id=99,
            trigger_source="subject_event_reopened",
        )

        self.assertEqual(
            repository.periods[0].status,
            SubjectPeriodStatus.REVIEW_REQUIRED,
        )
        self.assertEqual(repository.periods[1].status, SubjectPeriodStatus.ACTIVE)
        self.assertEqual(repository.corrected_period_ends, [])


class DjangoSubjectPeriodLifecycleRepositoryTests(TestCase):
    def setUp(self):
        self.now = datetime(2026, 7, 30, 8, 0, tzinfo=timezone.utc)
        self.study = Study.objects.create(
            created_at=self.now,
            updated_at=self.now,
            deleted=False,
            code="PERIOD_REPO",
            name="Period repository study",
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
            subject_code="SUBJ-001",
            screening_code="SCR-001",
            current_sequence=1,
        )
        self.period = SubjectPeriod.objects.create(
            created_at=self.now,
            updated_at=self.now,
            deleted=False,
            subject=self.subject,
            period_no=1,
            treatment_code="TREATMENT_A",
            status=SubjectPeriodStatus.PLANNED,
        )
        self.repository = DjangoSubjectPeriodLifecycleRepository()

    def test_transition_period_persists_status_and_audit_log(self):
        period_state = self.repository.list_periods_for_update(
            subject_id=self.subject.pk,
        )[0]

        self.repository.transition_period(
            period=period_state,
            to_status=SubjectPeriodStatus.ACTIVE,
            source_event_instance_id=None,
            trigger_source="subject_randomized",
            reason="randomization_assigned",
            facts={"subject_id": self.subject.pk},
            actor_user_id=99,
            now=self.now,
        )

        self.period.refresh_from_db()
        transition_log = SubjectPeriodTransitionLog.objects.get(period=self.period)
        self.assertEqual(self.period.status, SubjectPeriodStatus.ACTIVE)
        self.assertEqual(transition_log.from_status, SubjectPeriodStatus.PLANNED)
        self.assertEqual(transition_log.to_status, SubjectPeriodStatus.ACTIVE)
        self.assertEqual(transition_log.actor_user_id, 99)

    def test_lists_washout_period_when_planned_end_is_due(self):
        self.period.status = SubjectPeriodStatus.WASHOUT
        self.period.save(update_fields=["status"])
        SubjectPeriodMilestone.objects.create(
            period=self.period,
            milestone_code="WASHOUT_END_PLANNED",
            planned_at=self.now,
            status="planned",
        )

        subject_ids = self.repository.list_due_washout_subject_ids(
            as_of=self.now,
            limit=10,
        )

        self.assertEqual(subject_ids, [self.subject.pk])

    def test_due_processor_completes_washout_and_activates_next_period(self):
        self.period.status = SubjectPeriodStatus.WASHOUT
        self.period.save(update_fields=["status"])
        next_period = SubjectPeriod.objects.create(
            created_at=self.now,
            updated_at=self.now,
            deleted=False,
            subject=self.subject,
            period_no=2,
            treatment_code="TREATMENT_B",
            status=SubjectPeriodStatus.PLANNED,
        )
        SubjectPeriodMilestone.objects.create(
            period=self.period,
            milestone_code="WASHOUT_END_PLANNED",
            planned_at=self.now,
            status="planned",
        )

        results = SubjectPeriodLifecycleService(
            repository=self.repository,
        ).process_due_transitions(limit=10)

        self.period.refresh_from_db()
        next_period.refresh_from_db()
        self.assertTrue(results[0].has_changes)
        self.assertEqual(self.period.status, SubjectPeriodStatus.COMPLETED)
        self.assertEqual(next_period.status, SubjectPeriodStatus.ACTIVE)

    def test_manual_override_persists_statuses_milestones_and_audit(self):
        end_event_definition = EventDefinition.objects.create(
            created_at=self.now,
            updated_at=self.now,
            deleted=False,
            study=self.study,
            study_version="v1.0",
            code="VISIT8",
            name="Visit 8",
            event_type="visit_based",
            event_category="treatment",
            sequence_no=8,
            is_enabled=True,
        )
        end_event = SubjectEventInstance.objects.create(
            created_at=self.now,
            updated_at=self.now,
            deleted=False,
            study=self.study,
            subject=self.subject,
            event_definition=end_event_definition,
            study_version="v1.0",
            status="in_progress",
        )
        self.period.status = SubjectPeriodStatus.ACTIVE
        self.period.end_event_instance = end_event
        self.period.save(update_fields=["status", "end_event_instance"])
        next_period = SubjectPeriod.objects.create(
            created_at=self.now,
            updated_at=self.now,
            deleted=False,
            subject=self.subject,
            period_no=2,
            treatment_code="TREATMENT_B",
            status=SubjectPeriodStatus.PLANNED,
        )

        result = SubjectPeriodOverrideService(
            repository=self.repository,
        ).advance_to_next_period(
            study_id=self.study.pk,
            subject_id=self.subject.pk,
            actor_user_id=99,
            period_end_at=self.now,
            next_period_start_at=self.now,
            reason_code="paper_crf_delayed",
            reason_text="Paper CRF has not reached the site.",
            pending_data_acknowledged=True,
            clinical_transition_confirmed=True,
        )

        self.period.refresh_from_db()
        next_period.refresh_from_db()
        end_event.refresh_from_db()
        transition_override = SubjectPeriodTransitionOverride.objects.get(
            subject=self.subject,
        )
        self.assertTrue(result.applied)
        self.assertEqual(self.period.status, SubjectPeriodStatus.COMPLETED)
        self.assertEqual(next_period.status, SubjectPeriodStatus.ACTIVE)
        self.assertEqual(end_event.status, "in_progress")
        self.assertEqual(transition_override.reason_code, "paper_crf_delayed")
        self.assertEqual(transition_override.source_event_status, "in_progress")
        self.assertEqual(
            SubjectPeriodTransitionLog.objects.filter(
                subject=self.subject,
                trigger_source="manual_period_override",
            ).count(),
            2,
        )
        self.assertTrue(
            SubjectPeriodMilestone.objects.filter(
                period=next_period,
                milestone_code="PERIOD_START_ACTUAL",
                actual_at=self.now,
            ).exists()
        )


class _PeriodLifecycleRepositoryStub:
    def __init__(self, *, periods=None, event=None, washout_due=True):
        self.periods = list(
            periods
            or [
                _period(period_id=1, period_no=1),
                _period(period_id=2, period_no=2),
            ]
        )
        self.event = event
        self.transitions = []
        self.period_end_records = []
        self.period_start_records = []
        self.washout_end_records = []
        self.corrected_period_ends = []
        self.washout_due = washout_due

    def now(self):
        return datetime(2026, 7, 30, 8, 0, tzinfo=timezone.utc)

    def get_event_context(self, *, event_instance_id):
        if self.event and self.event.event_instance_id == event_instance_id:
            return self.event
        return None

    def list_periods_for_update(self, *, subject_id):
        return list(self.periods)

    def transition_period(self, *, period, to_status, reason, **kwargs):
        updated = replace(period, status=to_status)
        self.periods = [
            updated if candidate.id == period.id else candidate
            for candidate in self.periods
        ]
        self.transitions.append((period.id, period.status, to_status, reason))
        return updated

    def record_period_end(self, *, period, **kwargs):
        self.period_end_records.append(period.id)

    def record_period_start(self, *, period, **kwargs):
        self.period_start_records.append(period.id)

    def record_washout_end(self, *, period, **kwargs):
        self.washout_end_records.append(period.id)

    def correct_period_end(self, *, period, **kwargs):
        self.corrected_period_ends.append(period.id)

    def list_due_washout_subject_ids(self, *, as_of, limit):
        return []

    def is_washout_due(self, *, period, as_of):
        return self.washout_due


def _period(
    *,
    period_id,
    period_no,
    status=SubjectPeriodStatus.PLANNED,
    end_event_instance_id=None,
    washout_days=None,
    transition_rule_code=None,
):
    return SubjectPeriodState(
        id=period_id,
        subject_id=20,
        period_no=period_no,
        status=status,
        start_event_instance_id=None,
        end_event_instance_id=end_event_instance_id,
        washout_days=washout_days,
        transition_rule_code=transition_rule_code,
    )


def _event(*, event_instance_id, status, event_category="treatment"):
    return SubjectPeriodEventContext(
        event_instance_id=event_instance_id,
        subject_id=20,
        status=status,
        event_category=event_category,
    )
