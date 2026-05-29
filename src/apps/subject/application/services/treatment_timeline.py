from dataclasses import dataclass

from django.utils import timezone

from apps.subject.infrastructure.repositories.treatment_timeline import (
    DjangoSubjectTreatmentTimelineRepository,
)


@dataclass(frozen=True)
class SubjectTreatmentPeriodDTO:
    period_no: int
    treatment_code: str
    status: str
    sequence_period_id: int | None
    start_event_instance_id: int | None
    end_event_instance_id: int | None


@dataclass(frozen=True)
class SubjectTreatmentTimelineDTO:
    subject_id: int
    status: str
    randomization_sequence: str
    periods: tuple[SubjectTreatmentPeriodDTO, ...]


@dataclass(frozen=True)
class CurrentSubjectTreatmentDTO:
    subject_id: int
    status: str
    treatment_code: str | None = None
    current_phase: str | None = None
    randomization_sequence: str = ""
    last_treatment: str | None = None
    next_treatment: str | None = None


class SubjectTreatmentTimelineService:
    repository_class = DjangoSubjectTreatmentTimelineRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def get_subject_treatment_timeline(self, *, subject_id: int) -> SubjectTreatmentTimelineDTO:
        randomization = self.repository.get_randomization(subject_id=subject_id)
        if randomization is None:
            return SubjectTreatmentTimelineDTO(
                subject_id=subject_id,
                status="Not randomized",
                randomization_sequence="",
                periods=(),
            )
        periods = tuple(self._period_to_dto(period) for period in self.repository.list_periods(subject_id=subject_id))
        return SubjectTreatmentTimelineDTO(
            subject_id=subject_id,
            status="Randomized",
            randomization_sequence=randomization.randomization_sequence or "",
            periods=periods,
        )

    def get_current_subject_treatment(
        self,
        *,
        subject_id: int,
        event_instance_id: int | None = None,
        as_of=None,
    ) -> CurrentSubjectTreatmentDTO:
        as_of = as_of or timezone.now()
        randomization = self.repository.get_randomization(subject_id=subject_id)
        if randomization is None:
            return CurrentSubjectTreatmentDTO(subject_id=subject_id, status="Not randomized")

        periods = self.repository.list_periods(subject_id=subject_id)
        if event_instance_id is not None:
            matched = self._match_event_period(periods=periods, event_instance_id=event_instance_id)
            if matched is not None:
                return self._period_current_treatment(
                    subject_id=subject_id,
                    randomization_sequence=randomization.randomization_sequence or "",
                    period=matched,
                    as_of=as_of,
                )

        active = self._find_active_period(periods=periods, as_of=as_of)
        if active is not None:
            return CurrentSubjectTreatmentDTO(
                subject_id=subject_id,
                status="Active",
                treatment_code=active.treatment_code,
                current_phase="Treatment",
                randomization_sequence=randomization.randomization_sequence or "",
            )

        last_completed = self._find_last_completed_period(periods=periods, as_of=as_of)
        next_period = self._find_next_period(periods=periods, after_period=last_completed)
        if last_completed is not None and next_period is not None:
            return CurrentSubjectTreatmentDTO(
                subject_id=subject_id,
                status="Washout",
                current_phase="Washout",
                randomization_sequence=randomization.randomization_sequence or "",
                last_treatment=last_completed.treatment_code,
                next_treatment=next_period.treatment_code,
            )

        planned = next_period or (periods[0] if periods else None)
        return CurrentSubjectTreatmentDTO(
            subject_id=subject_id,
            status="Planned",
            treatment_code=getattr(planned, "treatment_code", None),
            current_phase="Planned",
            randomization_sequence=randomization.randomization_sequence or "",
            next_treatment=getattr(planned, "treatment_code", None),
        )

    @staticmethod
    def _period_to_dto(period) -> SubjectTreatmentPeriodDTO:
        return SubjectTreatmentPeriodDTO(
            period_no=period.period_no,
            treatment_code=period.treatment_code,
            status=period.status,
            sequence_period_id=period.sequence_period_id,
            start_event_instance_id=period.start_event_instance_id,
            end_event_instance_id=period.end_event_instance_id,
        )

    @staticmethod
    def _match_event_period(*, periods, event_instance_id):
        for period in periods:
            if period.start_event_instance_id == event_instance_id or period.end_event_instance_id == event_instance_id:
                return period
        return None

    def _period_current_treatment(self, *, subject_id, randomization_sequence, period, as_of):
        if self._period_has_actual_start(period=period, as_of=as_of) and not self._period_has_actual_end(period=period, as_of=as_of):
            return CurrentSubjectTreatmentDTO(
                subject_id=subject_id,
                status="Active",
                treatment_code=period.treatment_code,
                current_phase="Treatment",
                randomization_sequence=randomization_sequence,
            )
        return CurrentSubjectTreatmentDTO(
            subject_id=subject_id,
            status="Planned",
            treatment_code=period.treatment_code,
            current_phase="Planned",
            randomization_sequence=randomization_sequence,
            next_treatment=period.treatment_code,
        )

    def _find_active_period(self, *, periods, as_of):
        for period in periods:
            if self._period_has_actual_start(period=period, as_of=as_of) and not self._period_has_actual_end(period=period, as_of=as_of):
                return period
        return None

    def _find_last_completed_period(self, *, periods, as_of):
        completed = [period for period in periods if self._period_has_actual_end(period=period, as_of=as_of)]
        return completed[-1] if completed else None

    @staticmethod
    def _find_next_period(*, periods, after_period):
        if after_period is None:
            return periods[0] if periods else None
        for period in periods:
            if period.period_no > after_period.period_no:
                return period
        return None

    @staticmethod
    def _period_has_actual_start(*, period, as_of) -> bool:
        return any(
            milestone.actual_at and milestone.actual_at <= as_of
            for milestone in period.milestones
            if milestone.milestone_code in {"PERIOD_START_ACTUAL", "DOSE_ACTUAL"}
        )

    @staticmethod
    def _period_has_actual_end(*, period, as_of) -> bool:
        return any(
            milestone.actual_at and milestone.actual_at <= as_of
            for milestone in period.milestones
            if milestone.milestone_code in {"PERIOD_END_ACTUAL", "WASHOUT_START_ACTUAL"}
        )


__all__ = [
    "CurrentSubjectTreatmentDTO",
    "SubjectTreatmentPeriodDTO",
    "SubjectTreatmentTimelineDTO",
    "SubjectTreatmentTimelineService",
]
