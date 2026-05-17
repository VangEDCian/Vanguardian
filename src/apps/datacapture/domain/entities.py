from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class DataCapturePageStateSnapshot:
    id: int
    status: str
    final_data: str | None
    data_version: int
    current_entry_id: int | None
    crf_template_id: int
    subject_id: int
    visit_id: int
    study_id: int
    study_version: str
    event_definition_id: int


@dataclass(frozen=True)
class DataCapturePageEntrySnapshot:
    id: int
    page_state_id: int | None
    parent_entry_id: int | None
    entry_no: int
    entry_kind: str
    entry_version: str
    status: str
    data: str
    crf_template_id: int
    subject_id: int
    visit_id: int
    updated_by_id: int | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class DataCaptureFactMappingRule:
    id: int
    source_path: str
    fact_key: str
    operator: str
    expected_value: str | None
    value_type: str
    default_value: str | None = None
    field_code: str | None = None


@dataclass(frozen=True)
class PageEntryStateChangedEvent:
    entry_id: int
    page_state_id: int | None
    subject_id: int
    visit_id: int
    crf_template_id: int
    from_status: str | None
    to_status: str
    actor_user_id: int | None = None


@dataclass(frozen=True)
class PageEntryChangeStateResult:
    from_status: str | None
    to_status: str

    @property
    def changed(self) -> bool:
        return self.from_status != self.to_status

    def to_event(
        self,
        *,
        entry_id: int,
        page_state_id: int | None,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
        actor_user_id: int | None = None,
    ) -> PageEntryStateChangedEvent:
        return PageEntryStateChangedEvent(
            entry_id=entry_id,
            page_state_id=page_state_id,
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
            from_status=self.from_status,
            to_status=self.to_status,
            actor_user_id=actor_user_id,
        )


@dataclass(frozen=True)
class SaveDraftExecutionPlan:
    branch: Literal["create_initial", "update_draft", "correction_from_submitted", "noop_identical_submitted"]
    noop_page_status: str | None = None
    entry_state_change: PageEntryChangeStateResult | None = None


@dataclass(frozen=True)
class SubmitExecutionPlan:
    action: Literal["initial_submitted", "promote_draft", "replace_submitted", "noop_identical_submitted"]
    draft_entry_id: int | None = None
    supersede_other_submitted_before_promote: bool = False
    superseded_entry_snapshot: DataCapturePageEntrySnapshot | None = None
    entry_state_change: PageEntryChangeStateResult | None = None
    superseded_entry_state_change: PageEntryChangeStateResult | None = None


__all__ = [
    "DataCaptureFactMappingRule",
    "DataCapturePageEntrySnapshot",
    "DataCapturePageStateSnapshot",
    "PageEntryChangeStateResult",
    "PageEntryStateChangedEvent",
    "SaveDraftExecutionPlan",
    "SubmitExecutionPlan",
]
