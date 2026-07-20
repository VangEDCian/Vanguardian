from dataclasses import dataclass

from apps.subject.models import SubjectPeriod, SubjectRandomization


@dataclass(frozen=True)
class TreatmentMilestoneState:
    milestone_code: str
    actual_at: object


@dataclass(frozen=True)
class TreatmentPeriodState:
    period_no: int
    treatment_code: str
    status: str
    sequence_period_id: int | None
    start_event_instance_id: int | None
    end_event_instance_id: int | None
    milestones: tuple[TreatmentMilestoneState, ...]
    kit_code: str | None = None
    start_event_status: str | None = None
    end_event_status: str | None = None


@dataclass(frozen=True)
class SubjectRandomizationState:
    randomization_sequence: str


class DjangoSubjectTreatmentTimelineRepository:
    def get_randomization(self, *, subject_id: int) -> SubjectRandomizationState | None:
        return self.get_randomizations(subject_ids=(subject_id,)).get(subject_id)

    def get_randomizations(self, *, subject_ids) -> dict[int, SubjectRandomizationState]:
        randomizations = (
            SubjectRandomization.objects.filter(
                subject_id__in=subject_ids,
                deleted=False,
                slot_id__isnull=False,
            )
            .only("id", "subject_id", "randomization_sequence")
            .order_by("subject_id", "id")
        )
        return {
            randomization.subject_id: SubjectRandomizationState(
                randomization_sequence=randomization.randomization_sequence or ""
            )
            for randomization in randomizations
        }

    def list_periods(self, *, subject_id: int) -> list[TreatmentPeriodState]:
        return self.list_periods_by_subject_id(subject_ids=(subject_id,)).get(subject_id, [])

    def list_periods_by_subject_id(self, *, subject_ids) -> dict[int, list[TreatmentPeriodState]]:
        periods = (
            SubjectPeriod.objects.select_related("start_event_instance", "end_event_instance").prefetch_related(
                "milestones"
            )
            .filter(subject_id__in=subject_ids, deleted=False)
            .order_by("subject_id", "period_no", "id")
        )
        periods_by_subject_id = {}
        for period in periods:
            period_state = TreatmentPeriodState(
                period_no=period.period_no,
                treatment_code=period.treatment_code,
                status=period.status,
                sequence_period_id=period.sequence_period_id,
                start_event_instance_id=period.start_event_instance_id,
                end_event_instance_id=period.end_event_instance_id,
                milestones=tuple(
                    TreatmentMilestoneState(
                        milestone_code=milestone.milestone_code,
                        actual_at=milestone.actual_at,
                    )
                    for milestone in period.milestones.all()
                ),
                kit_code=period.kit_code,
                start_event_status=getattr(period.start_event_instance, "status", None),
                end_event_status=getattr(period.end_event_instance, "status", None),
            )
            periods_by_subject_id.setdefault(period.subject_id, []).append(period_state)
        return periods_by_subject_id


__all__ = [
    "DjangoSubjectTreatmentTimelineRepository",
    "SubjectRandomizationState",
    "TreatmentMilestoneState",
    "TreatmentPeriodState",
]
