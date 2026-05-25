import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


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
class DataCaptureFactForm:
    data: dict[str, Any] = field(default_factory=dict)
    status: str = ""
    open_queries: int = 0

    @classmethod
    def from_raw(
        cls,
        *,
        data: str | dict[str, Any] | None,
        status: str,
        open_queries: int = 0,
    ) -> "DataCaptureFactForm":
        parsed_data: dict[str, Any]
        if isinstance(data, dict):
            parsed_data = data
        elif data in (None, ""):
            parsed_data = {}
        else:
            try:
                loaded_data = json.loads(str(data))
            except (TypeError, ValueError, json.JSONDecodeError):
                loaded_data = {}
            parsed_data = loaded_data if isinstance(loaded_data, dict) else {}
        return cls(
            data=parsed_data,
            status=str(status or ""),
            open_queries=max(int(open_queries or 0), 0),
        )

    def to_jsonpath_value(self) -> dict[str, Any]:
        return {
            "data": self.data,
            "status": self.status,
            "open_queries": self.open_queries,
        }


@dataclass(frozen=True)
class DataCaptureFactSource:
    forms: dict[str, DataCaptureFactForm]
    current_form_code: str | None = None

    def to_jsonpath_context(self) -> dict[str, Any]:
        return {form_code: form.to_jsonpath_value() for form_code, form in self.forms.items()}

    def current_form_data(self) -> dict[str, Any] | None:
        if not self.current_form_code:
            return None
        form = self.forms.get(self.current_form_code)
        return form.data if form is not None else None


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
    "DataCaptureFactForm",
    "DataCaptureFactMappingRule",
    "DataCaptureFactSource",
    "DataCapturePageEntrySnapshot",
    "DataCapturePageStateSnapshot",
    "PageEntryChangeStateResult",
    "PageEntryStateChangedEvent",
    "SaveDraftExecutionPlan",
    "SubmitExecutionPlan",
]
