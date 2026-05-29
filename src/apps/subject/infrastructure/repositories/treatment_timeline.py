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


@dataclass(frozen=True)
class SubjectRandomizationState:
    randomization_sequence: str


class DjangoSubjectTreatmentTimelineRepository:
    def get_randomization(self, *, subject_id: int) -> SubjectRandomizationState | None:
        randomization = (
            SubjectRandomization.objects.filter(
                subject_id=subject_id,
                deleted=False,
                slot_id__isnull=False,
            )
            .only("id", "randomization_sequence")
            .first()
        )
        if randomization is None:
            return None
        return SubjectRandomizationState(randomization_sequence=randomization.randomization_sequence or "")

    def list_periods(self, *, subject_id: int) -> list[TreatmentPeriodState]:
        periods = (
            SubjectPeriod.objects.prefetch_related("milestones")
            .filter(subject_id=subject_id, deleted=False)
            .order_by("period_no", "id")
        )
        return [
            TreatmentPeriodState(
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
            )
            for period in periods
        ]


__all__ = [
    "DjangoSubjectTreatmentTimelineRepository",
    "SubjectRandomizationState",
    "TreatmentMilestoneState",
    "TreatmentPeriodState",
]
