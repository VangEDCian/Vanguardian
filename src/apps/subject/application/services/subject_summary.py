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


class SubjectSummaryQueryService:
    repository_class = DjangoSubjectSummaryRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def get_subject_summary(self, *, study_id: int, subject_id: int) -> dict | None:
        snapshot = self.repository.get_subject_summary_snapshot(
            study_id=study_id,
            subject_id=subject_id,
            snapshot_class=SubjectSummarySnapshotDTO,
            randomization_event_class=SubjectSummaryRandomizationEventDTO,
        )
        if snapshot is None:
            return None

        sections = [
            self._build_screening_section(snapshot),
            self._build_enrollment_section(snapshot),
            self._build_randomization_section(snapshot),
        ]
        return {
            "subject_id": snapshot.subject_id,
            "study_id": snapshot.study_id,
            "study_code": snapshot.study_code,
            "site_code": snapshot.site_code,
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
    def _build_randomization_section(cls, snapshot: SubjectSummarySnapshotDTO) -> dict | None:
        if not cls._should_show_randomization(snapshot):
            return None

        event = snapshot.randomization_event
        assignment_status = (
            cls._humanize_value(snapshot.randomization_status) if snapshot.randomization_status else "Not assigned"
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
                ("Randomization Number", snapshot.randomization_number),
                ("Scheme", snapshot.randomization_scheme_code),
                ("Arm", snapshot.randomization_arm_name),
                ("Slot", snapshot.randomization_slot_sequence),
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
        rows = [
            {
                "label": label,
                "value": value,
                "is_temporal": isinstance(value, (date, datetime)),
            }
            for label, value in items
            if cls._has_value(value)
        ]
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
    def _humanize_value(value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        return text.replace("_", " ").title()


__all__ = [
    "SubjectSummaryQueryService",
    "SubjectSummaryRandomizationEventDTO",
    "SubjectSummarySnapshotDTO",
]
