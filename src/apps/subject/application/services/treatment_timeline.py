from dataclasses import dataclass

from django.utils import timezone

from apps.subject.domain import SubjectPeriodStatus
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
    kit_code: str | None = None


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
    kit_code: str | None = None


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
        periods = self.repository.list_periods(subject_id=subject_id) if randomization is not None else []
        return self._resolve_current_subject_treatment(
            subject_id=subject_id,
            randomization=randomization,
            periods=periods,
            event_instance_id=event_instance_id,
            as_of=as_of,
        )

    def map_current_subject_treatment_by_subject_id(
        self,
        *,
        subject_ids,
        as_of=None,
    ) -> dict[int, CurrentSubjectTreatmentDTO]:
        subject_ids = tuple(dict.fromkeys(subject_ids))
        if not subject_ids:
            return {}
        as_of = as_of or timezone.now()
        randomizations = self.repository.get_randomizations(subject_ids=subject_ids)
        periods_by_subject_id = self.repository.list_periods_by_subject_id(subject_ids=subject_ids)
        return {
            subject_id: self._resolve_current_subject_treatment(
                subject_id=subject_id,
                randomization=randomizations.get(subject_id),
                periods=periods_by_subject_id.get(subject_id, []),
                event_instance_id=None,
                as_of=as_of,
            )
            for subject_id in subject_ids
        }

    def _resolve_current_subject_treatment(
        self,
        *,
        subject_id,
        randomization,
        periods,
        event_instance_id,
        as_of,
    ) -> CurrentSubjectTreatmentDTO:
        if randomization is None:
            return CurrentSubjectTreatmentDTO(subject_id=subject_id, status="Not randomized")

        if event_instance_id is not None:
            matched = self._match_event_period(periods=periods, event_instance_id=event_instance_id)
            if matched is not None:
                return self._period_current_treatment(
                    subject_id=subject_id,
                    randomization_sequence=randomization.randomization_sequence or "",
                    period=matched,
                    as_of=as_of,
                )

        active = self._find_active_period(periods=periods)
        if active is not None:
            return CurrentSubjectTreatmentDTO(
                subject_id=subject_id,
                status="Active",
                treatment_code=active.treatment_code,
                kit_code=getattr(active, "kit_code", None),
                current_phase="Treatment",
                randomization_sequence=randomization.randomization_sequence or "",
            )

        washout = self._find_period_by_status(
            periods=periods,
            status=SubjectPeriodStatus.WASHOUT,
        )
        if washout is not None:
            next_period = self._find_next_period(periods=periods, after_period=washout)
            return CurrentSubjectTreatmentDTO(
                subject_id=subject_id,
                status="Washout",
                current_phase="Washout",
                randomization_sequence=randomization.randomization_sequence or "",
                last_treatment=washout.treatment_code,
                next_treatment=getattr(next_period, "treatment_code", None),
            )

        last_completed = self._find_last_completed_period(periods=periods)
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
            kit_code=getattr(period, "kit_code", None),
        )

    @staticmethod
    def _match_event_period(*, periods, event_instance_id):
        for period in periods:
            if period.start_event_instance_id == event_instance_id or period.end_event_instance_id == event_instance_id:
                return period
        return None

    def _period_current_treatment(self, *, subject_id, randomization_sequence, period, as_of):
        period_status = SubjectPeriodStatus.normalize(period.status)
        if period_status == SubjectPeriodStatus.ACTIVE:
            return CurrentSubjectTreatmentDTO(
                subject_id=subject_id,
                status="Active",
                treatment_code=period.treatment_code,
                kit_code=getattr(period, "kit_code", None),
                current_phase="Treatment",
                randomization_sequence=randomization_sequence,
            )
        if period_status == SubjectPeriodStatus.WASHOUT:
            return CurrentSubjectTreatmentDTO(
                subject_id=subject_id,
                status="Washout",
                current_phase="Washout",
                randomization_sequence=randomization_sequence,
                last_treatment=period.treatment_code,
            )
        return CurrentSubjectTreatmentDTO(
            subject_id=subject_id,
            status="Planned",
            treatment_code=period.treatment_code,
            kit_code=getattr(period, "kit_code", None),
            current_phase="Planned",
            randomization_sequence=randomization_sequence,
            next_treatment=period.treatment_code,
        )

    def _find_active_period(self, *, periods):
        return self._find_period_by_status(
            periods=periods,
            status=SubjectPeriodStatus.ACTIVE,
        )

    def _find_last_completed_period(self, *, periods):
        completed = [
            period
            for period in periods
            if SubjectPeriodStatus.normalize(period.status)
            == SubjectPeriodStatus.COMPLETED
        ]
        return completed[-1] if completed else None

    @staticmethod
    def _find_period_by_status(*, periods, status):
        return next(
            (
                period
                for period in periods
                if SubjectPeriodStatus.normalize(period.status) == status
            ),
            None,
        )

    @staticmethod
    def _find_next_period(*, periods, after_period):
        if after_period is None:
            return periods[0] if periods else None
        for period in periods:
            if period.period_no > after_period.period_no:
                return period
        return None

__all__ = [
    "CurrentSubjectTreatmentDTO",
    "SubjectTreatmentPeriodDTO",
    "SubjectTreatmentTimelineDTO",
    "SubjectTreatmentTimelineService",
]
