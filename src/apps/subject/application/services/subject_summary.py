from dataclasses import dataclass
from datetime import date, datetime

from apps.subject.infrastructure.repositories.subject_summary import (
    DjangoSubjectSummaryRepository,
)


@dataclass(frozen=True)
class SubjectSummaryRandomizationEventDTO:
    event_name: str
    status: str
    opened_at: datetime | None
    planned_date: datetime | None


@dataclass(frozen=True)
class SubjectSummaryPeriodDTO:
    period_no: int
    treatment_code: str
    kit_code: str


@dataclass(frozen=True)
class SubjectSummarySnapshotDTO:
    subject_id: int
    study_id: int
    study_code: str
    site_code: str
    screening_code: str
    subject_code: str
    screening_date: datetime | None
    enrollment_is_enrolled: bool
    enrollment_status: str
    enrollment_date: date | None
    enrollment_status_datetime: datetime | None
    enrollment_reason_code: str
    enrollment_reason_text: str
    randomization_status: str
    randomization_datetime: datetime | None
    randomization_number: str
    randomization_scheme_code: str
    randomization_arm_name: str
    randomization_slot_sequence: int | None
    randomization_event: SubjectSummaryRandomizationEventDTO | None
    site_id: int = 0
    periods: tuple[SubjectSummaryPeriodDTO, ...] = ()


class SubjectSummaryQueryService:
    repository_class = DjangoSubjectSummaryRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def get_subject_summary(
        self,
        *,
        study_id: int,
        subject_id: int,
        include_assignment: bool = True,
    ) -> dict | None:
        snapshot = self.repository.get_subject_summary_snapshot(
            study_id=study_id,
            subject_id=subject_id,
            snapshot_class=SubjectSummarySnapshotDTO,
            randomization_event_class=SubjectSummaryRandomizationEventDTO,
            period_class=SubjectSummaryPeriodDTO,
        )
        if snapshot is None:
            return None

        sections = [
            self._build_screening_section(snapshot),
            self._build_enrollment_section(snapshot),
            self._build_randomization_section(snapshot, include_assignment=include_assignment),
        ]
        return {
            "subject_id": snapshot.subject_id,
            "study_id": snapshot.study_id,
            "study_code": snapshot.study_code,
            "site_code": snapshot.site_code,
            "site_id": snapshot.site_id,
            "title": snapshot.subject_code or snapshot.screening_code or "Subject Summary",
            "subtitle": self._build_subject_stage_label(snapshot),
            "screening_code": snapshot.screening_code,
            "subject_code": snapshot.subject_code,
            "sections": [section for section in sections if section is not None],
        }

    @classmethod
    def _build_subject_stage_label(cls, snapshot: SubjectSummarySnapshotDTO) -> str:
        if cls._should_show_randomization(snapshot):
            return "Randomization"
        if cls._should_show_enrollment(snapshot):
            return "Enrolled"
        return "Screening"

    @classmethod
    def _build_screening_section(cls, snapshot: SubjectSummarySnapshotDTO) -> dict | None:
        return cls._build_section(
            title="Screening",
            items=(
                ("Screening Code", snapshot.screening_code),
                ("Subject Code", snapshot.subject_code),
                ("Screening Date", snapshot.screening_date),
                ("Site", snapshot.site_code),
                ("Study", snapshot.study_code),
            ),
        )

    @classmethod
    def _build_enrollment_section(cls, snapshot: SubjectSummarySnapshotDTO) -> dict | None:
        if not cls._should_show_enrollment(snapshot):
            return None
        return cls._build_section(
            title="Enrollment",
            items=(
                ("Status", cls._humanize_value(snapshot.enrollment_status)),
                ("Enrollment Date", snapshot.enrollment_date),
                ("Status Datetime", snapshot.enrollment_status_datetime),
                ("Reason Code", snapshot.enrollment_reason_code),
                ("Reason Text", snapshot.enrollment_reason_text),
            ),
        )

    @classmethod
    def _build_randomization_section(
        cls,
        snapshot: SubjectSummarySnapshotDTO,
        *,
        include_assignment: bool = True,
    ) -> dict | None:
        if not cls._should_show_randomization(snapshot):
            return None

        event = snapshot.randomization_event
        assignment_status = (
            cls._humanize_value(snapshot.randomization_status) if snapshot.randomization_status else "Not assigned"
        )
        assignment_items = ()
        if include_assignment:
            period_items = []
            for period in snapshot.periods:
                period_items.extend(
                    (
                        (f"Period {period.period_no} Treatment", cls._humanize_value(period.treatment_code)),
                        (f"Period {period.period_no} Kit Code", period.kit_code),
                    )
                )
            if len(snapshot.periods) >= 2:
                second_period = snapshot.periods[1]
                period_items.append(
                    (
                        "Period 2 Instruction",
                        (
                            f"Continue period 2 with {cls._humanize_value(second_period.treatment_code)} "
                            f"using kit {second_period.kit_code}, without re-screening."
                        ),
                    )
                )
            assignment_items = (
                ("Randomization Number", snapshot.randomization_number),
                ("Scheme", snapshot.randomization_scheme_code),
                ("Arm", snapshot.randomization_arm_name),
                ("Slot", snapshot.randomization_slot_sequence),
                *period_items,
            )
        return cls._build_section(
            title="Randomization",
            items=(
                ("Randomization Event", getattr(event, "event_name", "")),
                ("Workflow Status", cls._humanize_value(getattr(event, "status", ""))),
                ("Opened At", getattr(event, "opened_at", None)),
                ("Planned Date", getattr(event, "planned_date", None)),
                ("Assignment Status", assignment_status),
                ("Randomization Date", snapshot.randomization_datetime),
                *assignment_items,
            ),
        )

    @staticmethod
    def _should_show_enrollment(snapshot: SubjectSummarySnapshotDTO) -> bool:
        return bool(snapshot.enrollment_is_enrolled)

    @staticmethod
    def _should_show_randomization(snapshot: SubjectSummarySnapshotDTO) -> bool:
        return bool(snapshot.randomization_event is not None or snapshot.randomization_status)

    @classmethod
    def _build_section(cls, *, title: str, items) -> dict | None:
        rows = []
        for label, value in items:
            if not cls._has_value(value):
                continue
            is_temporal = isinstance(value, (date, datetime))
            row = {
                "label": label,
                "value": value,
                "is_temporal": is_temporal,
            }
            if is_temporal:
                row["format_name"] = cls._temporal_format_name(value)
            rows.append(row)
        if not rows:
            return None
        return {
            "title": title,
            "items": rows,
        }

    @staticmethod
    def _has_value(value) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        return True

    @staticmethod
    def _temporal_format_name(value) -> str:
        if isinstance(value, datetime):
            return "DATETIME_FORMAT"
        return "DATE_FORMAT"

    @staticmethod
    def _humanize_value(value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        return text.replace("_", " ").title()


__all__ = [
    "SubjectSummaryQueryService",
    "SubjectSummaryPeriodDTO",
    "SubjectSummaryRandomizationEventDTO",
    "SubjectSummarySnapshotDTO",
]
