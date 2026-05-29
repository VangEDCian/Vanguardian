import json
from datetime import timedelta

from django.utils import timezone

from apps.study.models import RandomizationEvent, RandomizationSequencePeriod
from apps.subject.models import (
    Subject,
    SubjectEnrollment,
    SubjectEventInstance,
    SubjectMilestone,
    SubjectPeriod,
    SubjectPeriodMilestone,
    SubjectRandomization,
)


class DjangoSubjectRandomizationRepository:
    def now(self):
        return timezone.now()

    def get_subject_scope(self, *, subject_id: int):
        return (
            Subject.objects.select_related("study", "site")
            .filter(pk=subject_id, deleted=False)
            .only("id", "study_id", "site_id")
            .first()
        )

    def is_subject_enrolled_or_allowed_to_randomize(self, *, study_id: int, subject_id: int) -> bool:
        enrollment = (
            SubjectEnrollment.objects.filter(
                study_id=study_id,
                subject_id=subject_id,
                deleted=False,
            )
            .only("id", "is_enrolled", "status")
            .first()
        )
        if enrollment is None:
            return False
        return bool(enrollment.is_enrolled or str(enrollment.status).strip().lower() == "eligible")

    def get_existing_randomization_summary(self, *, subject_id: int, summary_class):
        randomization = (
            SubjectRandomization.objects.select_related("scheme", "arm", "slot")
            .filter(subject_id=subject_id, deleted=False)
            .first()
        )
        if randomization is None:
            return None
        return summary_class(
            subject_id=randomization.subject_id,
            study_id=randomization.study_id,
            site_id=randomization.site_id,
            scheme_id=randomization.scheme_id,
            scheme_code=getattr(randomization.scheme, "code", "") if randomization.scheme_id else "",
            arm_id=randomization.arm_id,
            arm_code=getattr(randomization.arm, "arm_code", "") if randomization.arm_id else "",
            arm_name=getattr(randomization.arm, "arm_name", "") if randomization.arm_id else "",
            slot_id=randomization.slot_id,
            sequence_no=getattr(randomization.slot, "sequence_no", None) if randomization.slot_id else None,
            randomization_event_id=None,
            randomization_status=randomization.randomization_status or "",
            randomization_datetime=randomization.randomization_datetime,
            randomization_number=randomization.randomization_number or "",
            randomization_source=randomization.randomization_source or "",
            period_count=self.count_subject_periods(subject_id=subject_id),
        )

    def record_assignment(
        self,
        *,
        subject,
        assignment,
        event_instance_id: int | None,
        actor_user_id: int | None,
        source: str,
        reason_code: str | None,
        reason_text: str | None,
        now,
        summary_class,
    ):
        randomization = (
            SubjectRandomization.objects.select_for_update()
            .filter(subject_id=subject.pk, deleted=False)
            .first()
        )
        before_data = self._serialize_subject_randomization(randomization)
        randomization_number = str(assignment.sequence_no)
        event = RandomizationEvent.objects.create(
            created_at=now,
            event_type="Assigned",
            randomization_status="assigned",
            randomization_datetime=now,
            randomization_sequence=assignment.arm_code,
            randomization_number=randomization_number,
            randomization_source=source,
            reason_code=reason_code,
            reason_text=reason_text,
            before_data=json.dumps(before_data, ensure_ascii=True, sort_keys=True, default=str),
            after_data="{}",
            subject_id=subject.pk,
            study_id=subject.study_id,
            scheme_id=assignment.scheme_id,
            arm_id=assignment.arm_id,
            slot_id=assignment.slot_id,
            actor_id=actor_user_id,
            created_by_id=actor_user_id,
        )

        values = {
            "updated_at": now,
            "deleted": False,
            "randomization_status": "assigned",
            "randomization_datetime": now,
            "randomization_sequence": assignment.arm_code,
            "randomization_number": randomization_number,
            "randomization_source": source,
            "randomized_by_id": actor_user_id,
            "scheme_id": assignment.scheme_id,
            "arm_id": assignment.arm_id,
            "slot_id": assignment.slot_id,
            "site_id": subject.site_id,
            "study_id": subject.study_id,
            "updated_by_id": actor_user_id,
        }
        if randomization is None:
            values.update(
                {
                    "created_at": now,
                    "subject_id": subject.pk,
                    "created_by_id": actor_user_id,
                }
            )
            randomization = SubjectRandomization.objects.create(**values)
        else:
            for field, value in values.items():
                setattr(randomization, field, value)
            randomization.save(update_fields=list(values.keys()))

        period_count = self.ensure_subject_periods(
            subject_id=subject.pk,
            arm_id=assignment.arm_id,
            actor_user_id=actor_user_id,
            now=now,
        )
        self.upsert_randomized_subject_milestone(
            subject=subject,
            event_instance_id=event_instance_id,
            randomization_event_id=event.pk,
            occurred_at=now,
            actor_user_id=actor_user_id,
            now=now,
        )

        after_data = self._serialize_subject_randomization(randomization)
        after_data["randomization_event_id"] = event.pk
        event.after_data = json.dumps(after_data, ensure_ascii=True, sort_keys=True, default=str)
        event.save(update_fields=["after_data"])

        return summary_class(
            subject_id=subject.pk,
            study_id=subject.study_id,
            site_id=subject.site_id,
            scheme_id=assignment.scheme_id,
            scheme_code=assignment.scheme_code,
            arm_id=assignment.arm_id,
            arm_code=assignment.arm_code,
            arm_name=assignment.arm_name,
            slot_id=assignment.slot_id,
            sequence_no=assignment.sequence_no,
            randomization_event_id=event.pk,
            randomization_status="assigned",
            randomization_datetime=now,
            randomization_number=randomization_number,
            randomization_source=source,
            period_count=period_count,
        )

    def ensure_subject_periods(self, *, subject_id: int, arm_id: int | None, actor_user_id: int | None, now) -> int:
        if arm_id is None:
            return 0
        sequence_periods = list(
            RandomizationSequencePeriod.objects.filter(
                arm_id=arm_id,
                deleted=False,
            ).order_by("period_no", "display_order", "id")
        )
        for sequence_period in sequence_periods:
            start_event = self._find_event_instance(
                subject_id=subject_id,
                event_definition_id=sequence_period.start_event_definition_id,
            )
            end_event = self._find_event_instance(
                subject_id=subject_id,
                event_definition_id=sequence_period.end_event_definition_id,
            )
            period, created = SubjectPeriod.objects.get_or_create(
                subject_id=subject_id,
                period_no=sequence_period.period_no,
                defaults={
                    "created_at": now,
                    "updated_at": now,
                    "deleted": False,
                    "treatment_code": sequence_period.treatment_code,
                    "status": "Planned",
                    "sequence_period_id": sequence_period.pk,
                    "start_event_instance_id": getattr(start_event, "pk", None),
                    "end_event_instance_id": getattr(end_event, "pk", None),
                    "created_by_id": actor_user_id,
                    "updated_by_id": actor_user_id,
                },
            )
            if not created:
                updates = {
                    "updated_at": now,
                    "treatment_code": sequence_period.treatment_code,
                    "sequence_period_id": sequence_period.pk,
                    "start_event_instance_id": getattr(start_event, "pk", None),
                    "end_event_instance_id": getattr(end_event, "pk", None),
                    "updated_by_id": actor_user_id,
                }
                for field, value in updates.items():
                    setattr(period, field, value)
                period.save(update_fields=list(updates.keys()))

            self._ensure_period_planned_milestones(
                period=period,
                sequence_period=sequence_period,
                start_event=start_event,
                end_event=end_event,
                actor_user_id=actor_user_id,
                now=now,
            )
        return len(sequence_periods)

    def count_subject_periods(self, *, subject_id: int) -> int:
        return SubjectPeriod.objects.filter(subject_id=subject_id, deleted=False).count()

    def upsert_randomized_subject_milestone(
        self,
        *,
        subject,
        event_instance_id: int | None,
        randomization_event_id: int,
        occurred_at,
        actor_user_id: int | None,
        now,
    ):
        milestone, created = SubjectMilestone.objects.get_or_create(
            subject_id=subject.pk,
            milestone_code="RANDOMIZED",
            is_current=True,
            defaults={
                "study_id": subject.study_id,
                "site_id": subject.site_id,
                "milestone_label": "Randomized",
                "occurred_at": occurred_at,
                "occurred_date": occurred_at.date() if occurred_at else None,
                "occurred_time": occurred_at.time() if occurred_at else None,
                "date_precision": "datetime",
                "recorded_at": now,
                "recorded_by_id": actor_user_id,
                "source_type": "EDC_ACTION",
                "source_context": "study",
                "source_object_type": "study_randomization_event",
                "source_object_id": randomization_event_id,
                "source_event_instance_id": event_instance_id,
                "status": "confirmed",
                "confirmed_by_id": actor_user_id,
                "confirmed_at": now,
                "created_at": now,
                "updated_at": now,
                "deleted": False,
                "created_by_id": actor_user_id,
                "updated_by_id": actor_user_id,
            },
        )
        if created:
            return milestone
        milestone.occurred_at = occurred_at
        milestone.occurred_date = occurred_at.date() if occurred_at else None
        milestone.occurred_time = occurred_at.time() if occurred_at else None
        milestone.recorded_at = now
        milestone.recorded_by_id = actor_user_id
        milestone.source_object_id = randomization_event_id
        milestone.source_event_instance_id = event_instance_id
        milestone.status = "confirmed"
        milestone.confirmed_by_id = actor_user_id
        milestone.confirmed_at = now
        milestone.updated_at = now
        milestone.updated_by_id = actor_user_id
        milestone.save(
            update_fields=[
                "occurred_at",
                "occurred_date",
                "occurred_time",
                "recorded_at",
                "recorded_by_id",
                "source_object_id",
                "source_event_instance_id",
                "status",
                "confirmed_by_id",
                "confirmed_at",
                "updated_at",
                "updated_by_id",
            ]
        )
        return milestone

    def _ensure_period_planned_milestones(
        self,
        *,
        period,
        sequence_period,
        start_event,
        end_event,
        actor_user_id,
        now,
    ):
        start_planned_at = self._event_planned_at(start_event)
        end_planned_at = self._event_planned_at(end_event)
        self._get_or_create_period_milestone(
            period=period,
            milestone_code="PERIOD_START_PLANNED",
            planned_at=start_planned_at,
            actor_user_id=actor_user_id,
            now=now,
        )
        self._get_or_create_period_milestone(
            period=period,
            milestone_code="DOSE_PLANNED",
            planned_at=start_planned_at,
            actor_user_id=actor_user_id,
            now=now,
        )
        self._get_or_create_period_milestone(
            period=period,
            milestone_code="PERIOD_END_PLANNED",
            planned_at=end_planned_at,
            actor_user_id=actor_user_id,
            now=now,
        )
        if sequence_period.washout_days:
            self._get_or_create_period_milestone(
                period=period,
                milestone_code="WASHOUT_START_PLANNED",
                planned_at=end_planned_at,
                actor_user_id=actor_user_id,
                now=now,
            )
            washout_end = end_planned_at + timedelta(days=sequence_period.washout_days) if end_planned_at else None
            self._get_or_create_period_milestone(
                period=period,
                milestone_code="WASHOUT_END_PLANNED",
                planned_at=washout_end,
                actor_user_id=actor_user_id,
                now=now,
            )

    @staticmethod
    def _get_or_create_period_milestone(*, period, milestone_code, planned_at, actor_user_id, now):
        return SubjectPeriodMilestone.objects.get_or_create(
            period_id=period.pk,
            milestone_code=milestone_code,
            defaults={
                "planned_at": planned_at,
                "actual_at": None,
                "status": "planned",
                "source_context": "study",
                "source_object_type": "study_randomization_sequence_period",
                "source_object_id": period.sequence_period_id,
                "recorded_at": now,
                "recorded_by_id": actor_user_id,
            },
        )

    @staticmethod
    def _find_event_instance(*, subject_id, event_definition_id):
        if event_definition_id is None:
            return None
        return (
            SubjectEventInstance.objects.filter(
                subject_id=subject_id,
                event_definition_id=event_definition_id,
                deleted=False,
            )
            .order_by("repeat_index", "id")
            .first()
        )

    @staticmethod
    def _event_planned_at(event_instance):
        if event_instance is None:
            return None
        return event_instance.planned_date or event_instance.target_date

    @staticmethod
    def _serialize_subject_randomization(randomization):
        if randomization is None:
            return {}
        return {
            "id": randomization.pk,
            "subject_id": randomization.subject_id,
            "study_id": randomization.study_id,
            "site_id": randomization.site_id,
            "scheme_id": randomization.scheme_id,
            "arm_id": randomization.arm_id,
            "slot_id": randomization.slot_id,
            "randomization_status": randomization.randomization_status,
            "randomization_datetime": randomization.randomization_datetime,
            "randomization_sequence": randomization.randomization_sequence,
            "randomization_number": randomization.randomization_number,
            "randomization_source": randomization.randomization_source,
        }


__all__ = ["DjangoSubjectRandomizationRepository"]
