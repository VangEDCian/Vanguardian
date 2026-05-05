import json
from dataclasses import dataclass

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.core.choices import DataCapturePageEntryStatusChoices, DataCapturePageStateStatusChoices
from apps.datacapture.application.commands import (
    DeleteDraftPageCommand,
    SavePageCommand,
    SubmitFieldChangeReason,
    SubmitPageCommand,
)
from apps.datacapture.domain.exceptions import (
    InvalidPagePayloadError,
    PageNotEditableError,
    UnsupportedEntryStatusError,
)
from apps.datacapture.domain.services.page_capture_save_submit import (
    assert_page_editable_for_capture,
    build_submit_execution_plan,
    resolve_save_draft_execution_plan,
)
from apps.datacapture.infrastructure.repositories import DjangoDataCapturePageRepository
from apps.reconcile.public import create_data_queries_for_page_change_reasons


@dataclass(frozen=True)
class SavePageResult:
    entry_id: int | None
    entry_status: str
    page_status: str | None
    needs_confirmation: bool = False
    created_new_entry: bool = False


@dataclass(frozen=True)
class SubmitPageResult:
    entry_id: int | None
    entry_status: str
    page_status: str
    created_new_entry: bool = False


@dataclass(frozen=True)
class DeleteDraftPageResult:
    entry_id: int | None
    entry_status: str
    page_status: str


def _raise_as_http(exc: PageNotEditableError | InvalidPagePayloadError | UnsupportedEntryStatusError) -> None:
    if isinstance(exc, PageNotEditableError):
        raise PermissionDenied("Page is not editable") from exc
    raise ValidationError([str(exc)]) from exc


_DATE_PART_SUFFIXES = ("__day", "__month", "__year", "__time")


def _load_payload_map(raw_payload: str | None) -> dict:
    try:
        payload = json.loads(raw_payload or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _canonical_field_key(raw_key: str) -> str:
    key = str(raw_key or "").strip()
    for suffix in _DATE_PART_SUFFIXES:
        if key.endswith(suffix):
            return key[: -len(suffix)]
    return key


def _normalize_value(raw_value):
    if raw_value is None:
        return ""
    return raw_value


def _resolve_canonical_value(payload_map: dict, canonical_key: str):
    date_keys = [f"{canonical_key}{suffix}" for suffix in _DATE_PART_SUFFIXES]
    has_date_parts = any(date_key in payload_map for date_key in date_keys)
    if has_date_parts:
        return {
            "__day": _normalize_value(payload_map.get(f"{canonical_key}__day")),
            "__month": _normalize_value(payload_map.get(f"{canonical_key}__month")),
            "__year": _normalize_value(payload_map.get(f"{canonical_key}__year")),
            "__time": _normalize_value(payload_map.get(f"{canonical_key}__time")),
        }
    return _normalize_value(payload_map.get(canonical_key))


def _resolve_changed_field_keys(*, baseline_payload: dict, candidate_payload: dict) -> list[str]:
    canonical_keys: set[str] = set()
    for key in baseline_payload:
        canonical = _canonical_field_key(key)
        if canonical:
            canonical_keys.add(canonical)
    for key in candidate_payload:
        canonical = _canonical_field_key(key)
        if canonical:
            canonical_keys.add(canonical)
    changed_keys: list[str] = []
    for canonical_key in sorted(canonical_keys):
        before_value = _resolve_canonical_value(baseline_payload, canonical_key)
        after_value = _resolve_canonical_value(candidate_payload, canonical_key)
        if before_value != after_value:
            changed_keys.append(canonical_key)
    return changed_keys


def _build_change_reason_map(
    reasons: tuple[SubmitFieldChangeReason, ...],
) -> dict[str, SubmitFieldChangeReason]:
    normalized: dict[str, SubmitFieldChangeReason] = {}
    for item in reasons:
        canonical_key = _canonical_field_key(item.field_key)
        if not canonical_key:
            continue
        normalized[canonical_key] = SubmitFieldChangeReason(
            field_key=canonical_key,
            field_label=str(item.field_label or "").strip(),
            reason=str(item.reason or "").strip(),
        )
    return normalized


class DataCaptureSaveSubmitPageService:

    repository_class = DjangoDataCapturePageRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def _upsert_draft_page_state(self, command: SavePageCommand) -> None:
        self.repository.upsert_page_state(
            subject_id=command.subject_id,
            visit_id=command.visit_id,
            crf_template_id=command.crf_template_id,
            data=command.data,
            status=DataCapturePageStateStatusChoices.DRAFT,
            actor_user_id=command.actor_user_id,
        )

    @transaction.atomic
    def save(self, command: SavePageCommand) -> SavePageResult:
        page_state = self.repository.get_page_state_by_scope(
            subject_id=command.subject_id,
            visit_id=command.visit_id,
            crf_template_id=command.crf_template_id,
        )
        latest = self.repository.get_current_entry(
            subject_id=command.subject_id,
            visit_id=command.visit_id,
            crf_template_id=command.crf_template_id,
        )
        try:
            plan = resolve_save_draft_execution_plan(
                page_state=page_state,
                latest=latest,
                payload=command.data,
            )
        except PageNotEditableError as exc:
            _raise_as_http(exc)
        except (InvalidPagePayloadError, UnsupportedEntryStatusError) as exc:
            _raise_as_http(exc)

        if plan.branch == "noop_identical_submitted":
            assert latest is not None
            return SavePageResult(
                entry_id=latest.id,
                entry_status=latest.status,
                page_status=plan.noop_page_status,
                needs_confirmation=False,
                created_new_entry=False,
            )

        if plan.branch == "create_initial":
            entry = self.repository.create_initial_entry(
                subject_id=command.subject_id,
                visit_id=command.visit_id,
                crf_template_id=command.crf_template_id,
                data=command.data,
                actor_user_id=command.actor_user_id,
            )
            self._upsert_draft_page_state(command)
            return SavePageResult(
                entry_id=entry.pk,
                entry_status=entry.status,
                page_status="draft",
                needs_confirmation=False,
                created_new_entry=True,
            )

        if plan.branch == "update_draft":
            refreshed = self.repository.update_latest_draft_entry_data(
                subject_id=command.subject_id,
                visit_id=command.visit_id,
                crf_template_id=command.crf_template_id,
                data=command.data,
                actor_user_id=command.actor_user_id,
            )
            snapshot = refreshed or latest
            assert snapshot is not None
            self._upsert_draft_page_state(command)
            return SavePageResult(
                entry_id=snapshot.id,
                entry_status=snapshot.status,
                page_status="draft",
                needs_confirmation=False,
                created_new_entry=False,
            )

        if plan.branch == "correction_from_submitted":
            entry = self.repository.create_correction_draft_from_submitted_entry(
                subject_id=command.subject_id,
                visit_id=command.visit_id,
                crf_template_id=command.crf_template_id,
                data=command.data,
                actor_user_id=command.actor_user_id,
            )
            self._upsert_draft_page_state(command)
            return SavePageResult(
                entry_id=entry.pk,
                entry_status=entry.status,
                page_status="draft",
                needs_confirmation=True,
                created_new_entry=True,
            )

        raise RuntimeError(f"Unhandled save draft branch: {plan.branch!r}")

    @transaction.atomic
    def submit(self, command: SubmitPageCommand) -> SubmitPageResult:
        page_state = self.repository.get_page_state_by_scope(
            subject_id=command.subject_id,
            visit_id=command.visit_id,
            crf_template_id=command.crf_template_id,
        )
        latest = self.repository.get_current_entry(
            subject_id=command.subject_id,
            visit_id=command.visit_id,
            crf_template_id=command.crf_template_id,
        )
        has_other = False
        if latest is not None and latest.status == DataCapturePageEntryStatusChoices.DRAFT:
            has_other = self.repository.has_other_submitted_entry(
                subject_id=command.subject_id,
                visit_id=command.visit_id,
                crf_template_id=command.crf_template_id,
                exclude_entry_id=latest.id,
            )
        latest_submitted = self.repository.get_latest_submitted_entry(
            subject_id=command.subject_id,
            visit_id=command.visit_id,
            crf_template_id=command.crf_template_id,
        )
        try:
            plan = build_submit_execution_plan(
                page_state=page_state,
                latest=latest,
                has_other_submitted_entry=has_other,
                payload=command.data,
            )
        except PageNotEditableError as exc:
            _raise_as_http(exc)
        except (InvalidPagePayloadError, UnsupportedEntryStatusError) as exc:
            _raise_as_http(exc)

        changed_field_keys: list[str] = []
        reasons_for_changed_fields: list[dict[str, str]] = []
        if latest_submitted is not None and (latest is None or latest_submitted.id != latest.id):
            baseline_payload = _load_payload_map(latest_submitted.data)
            candidate_payload = _load_payload_map(command.data)
            changed_field_keys = _resolve_changed_field_keys(
                baseline_payload=baseline_payload,
                candidate_payload=candidate_payload,
            )
            if changed_field_keys:
                reason_map = _build_change_reason_map(command.change_reasons)
                missing_reason_fields = [
                    field_key for field_key in changed_field_keys if not reason_map.get(field_key) or not reason_map[field_key].reason
                ]
                if missing_reason_fields:
                    raise ValidationError(["Change reason is required for all updated fields before submit."])
                reasons_for_changed_fields = [
                    {
                        "field_key": field_key,
                        "field_label": reason_map[field_key].field_label or field_key,
                        "reason": reason_map[field_key].reason,
                    }
                    for field_key in changed_field_keys
                ]

        entry = self.repository.execute_submit_plan(
            subject_id=command.subject_id,
            visit_id=command.visit_id,
            crf_template_id=command.crf_template_id,
            plan=plan,
            data=command.data,
            actor_user_id=command.actor_user_id,
        )
        page_state = self.repository.upsert_page_state(
            subject_id=command.subject_id,
            visit_id=command.visit_id,
            crf_template_id=command.crf_template_id,
            data=command.data,
            status=DataCapturePageStateStatusChoices.SUBMITTED,
            actor_user_id=command.actor_user_id,
        )
        if reasons_for_changed_fields:
            create_data_queries_for_page_change_reasons(
                page_state_id=page_state.id,
                crf_template_id=command.crf_template_id,
                reasons=reasons_for_changed_fields,
                actor_user_id=command.actor_user_id,
            )
        return SubmitPageResult(
            entry_id=entry.pk,
            entry_status=DataCapturePageEntryStatusChoices.SUBMITTED,
            page_status=page_state.status,
            created_new_entry=plan.action in {"initial_submitted", "replace_submitted"},
        )

    @transaction.atomic
    def delete_latest_draft(self, command: DeleteDraftPageCommand) -> DeleteDraftPageResult:
        page_state = self.repository.get_page_state_by_scope(
            subject_id=command.subject_id,
            visit_id=command.visit_id,
            crf_template_id=command.crf_template_id,
        )
        try:
            if page_state is not None:
                assert_page_editable_for_capture(page_state)
        except PageNotEditableError as exc:
            _raise_as_http(exc)

        canceled_entry = self.repository.cancel_latest_draft_entry(
            subject_id=command.subject_id,
            visit_id=command.visit_id,
            crf_template_id=command.crf_template_id,
            actor_user_id=command.actor_user_id,
        )
        if canceled_entry is None:
            raise ValidationError(["No active draft version to delete."])

        latest_submitted = self.repository.get_latest_submitted_entry(
            subject_id=command.subject_id,
            visit_id=command.visit_id,
            crf_template_id=command.crf_template_id,
        )
        if latest_submitted is not None:
            page_state = self.repository.upsert_page_state(
                subject_id=command.subject_id,
                visit_id=command.visit_id,
                crf_template_id=command.crf_template_id,
                data=latest_submitted.data,
                status=DataCapturePageStateStatusChoices.SUBMITTED,
                actor_user_id=command.actor_user_id,
            )
            return DeleteDraftPageResult(
                entry_id=canceled_entry.id,
                entry_status=DataCapturePageEntryStatusChoices.CANCELED,
                page_status=page_state.status,
            )

        page_state = self.repository.upsert_page_state(
            subject_id=command.subject_id,
            visit_id=command.visit_id,
            crf_template_id=command.crf_template_id,
            data=canceled_entry.data,
            status=DataCapturePageStateStatusChoices.CANCELED,
            actor_user_id=command.actor_user_id,
        )
        return DeleteDraftPageResult(
            entry_id=canceled_entry.id,
            entry_status=DataCapturePageEntryStatusChoices.CANCELED,
            page_status=page_state.status,
        )
