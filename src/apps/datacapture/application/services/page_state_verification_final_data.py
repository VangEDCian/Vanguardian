import json
from typing import Any

from django.db import OperationalError, ProgrammingError

from apps.core.choices import (
    DataCaptureFieldReviewTypeChoices,
)
from apps.core.form_data_document import flatten_form_data_for_export, normalize_form_data
from apps.crf.models import CrfFieldReviewPolicy
from apps.crf.public import CrfContextAdapter
from apps.datacapture.application.commands import TriggerPageStateEventTransitionCommand
from apps.datacapture.application.exceptions import DataCaptureValidationError
from apps.datacapture.application.services.trigger_event_transition import DataCapturePageStateEventTransitionService
from apps.datacapture.application.validators import DataCapturePageStateVerificationValidator
from apps.datacapture.domain.status import DataCapturePageState
from apps.datacapture.infrastructure.repositories import DjangoDataCapturePageRepository
from apps.reconcile.application.services.dataquery_read import ReconcileDataQueryReadService
from apps.subject.public import SubjectEventLifecycleAdapter


class DataCapturePageStateVerificationFinalDataService:
    """Verify field reviews and page state without mutating clinical ``final_data``."""

    validator_class = DataCapturePageStateVerificationValidator
    subject_event_lifecycle_adapter_class = SubjectEventLifecycleAdapter
    event_transition_service_class = DataCapturePageStateEventTransitionService

    def __init__(
        self,
        repository=None,
        reconcile_read_service=None,
        subject_event_lifecycle_adapter=None,
        event_transition_service=None,
    ):
        self.repository = repository or DjangoDataCapturePageRepository()
        self.reconcile_read_service = reconcile_read_service or ReconcileDataQueryReadService()
        self.subject_event_lifecycle_adapter = (
            subject_event_lifecycle_adapter or self.subject_event_lifecycle_adapter_class()
        )
        self.event_transition_service = event_transition_service or self.event_transition_service_class()
        self.validator = self.validator_class()

    @staticmethod
    def _load_json_dict(raw_value) -> dict[str, Any]:
        if not raw_value or not str(raw_value).strip():
            return {}
        try:
            loaded = json.loads(raw_value)
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        if not isinstance(loaded, dict):
            return {}
        doc = normalize_form_data(loaded, strict=False)
        return flatten_form_data_for_export(doc, repeat_strategy="legacy_repeat_suffix")

    @staticmethod
    def _normalize_checked_ids(checked_field_template_ids: list[int] | None) -> set[int]:
        checked_set: set[int] = set()
        for raw_id in checked_field_template_ids or []:
            try:
                checked_set.add(int(raw_id))
            except (TypeError, ValueError):
                continue
        return checked_set

    @staticmethod
    def _field_template_ids(field_rows: list[dict[str, Any]]) -> tuple[int, ...]:
        ids: list[int] = []
        for field_row in field_rows or []:
            try:
                ids.append(int(field_row.get("id")))
            except (TypeError, ValueError):
                continue
        return tuple(ids)

    @staticmethod
    def _value_snapshot_for_field(
        *,
        entry_payload: dict[str, Any],
        field_row: dict[str, Any],
        field_template_id: int,
    ) -> str:
        field_key = str(field_row.get("field_key") or "").strip() or f"FIELD_{int(field_template_id)}"
        raw_value = entry_payload.get(field_key, "")
        value = "" if raw_value is None else str(raw_value)
        return json.dumps({field_key: value}, ensure_ascii=False, sort_keys=True)

    def _get_reviewable_page_state_or_raise(self, *, subject_id: int, visit_id: int, crf_template_id: int):
        snapshot = self.repository.get_page_state(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
        )
        self.validator.require_page_state(snapshot)
        self.validator.require_verify_status(snapshot.status)
        return snapshot

    def _required_field_template_ids(self, *, snapshot, all_field_template_ids: tuple[int, ...]) -> tuple[int, ...]:
        try:
            policy_ids = tuple(
                CrfFieldReviewPolicy.objects.filter(
                    study_id=snapshot.study_id,
                    study_version=snapshot.study_version,
                    crf_template_id=snapshot.crf_template_id,
                    review_type=DataCaptureFieldReviewTypeChoices.DATA_REVIEW,
                    is_required_for_page_verify=True,
                    is_enabled=True,
                    deleted=False,
                ).values_list("field_template_id", flat=True)
            )
        except (OperationalError, ProgrammingError):
            policy_ids = ()
        return tuple(int(field_id) for field_id in (policy_ids or all_field_template_ids))

    def merge_checked_field_template_ids(
        self,
        *,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
        checked_field_template_ids: list[int],
        actor_user_id: int | None = None,
    ) -> tuple[bool, str, list[str]]:
        snapshot = self._get_reviewable_page_state_or_raise(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
        )
        checked_set = self._normalize_checked_ids(checked_field_template_ids)
        for field_template_id in sorted(checked_set):
            if self.reconcile_read_service.has_open_query_for_page_field(
                page_state_id=snapshot.id,
                field_template_id=field_template_id,
            ):
                raise DataCaptureValidationError("yêu cầu đóng Query trước khi verify")

        page_state = self.repository.start_page_review(
            page_state_id=snapshot.id,
            actor_user_id=actor_user_id,
        )
        snapshot = self.repository.get_page_state(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
        )
        self.validator.require_page_state(snapshot)

        field_rows = CrfContextAdapter().list_template_fields_with_ui_config(template_id=crf_template_id)
        field_template_ids = self._field_template_ids(field_rows)
        self.validator.require_field_definitions(field_template_ids)

        self.repository.ensure_field_reviews_for_page(
            page_state_id=page_state.pk,
            field_template_ids=field_template_ids,
            data_version=snapshot.data_version,
            actor_user_id=actor_user_id,
            review_type=DataCaptureFieldReviewTypeChoices.DATA_REVIEW,
        )

        latest_entry = self.repository.get_current_entry(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
        )
        entry_payload = self._load_json_dict(latest_entry.data if latest_entry is not None else "{}")
        blockers: list[str] = []
        field_row_by_id = {}
        for field_row in field_rows:
            try:
                field_row_by_id[int(field_row.get("id"))] = field_row
            except (TypeError, ValueError):
                continue

        for field_template_id in sorted(checked_set & set(field_template_ids)):
            if self.reconcile_read_service.has_active_blocking_query_for_page_field(
                page_state_id=snapshot.id,
                field_template_id=field_template_id,
            ):
                blockers.append(f"field_blocked_by_query:{field_template_id}")
                continue
            self.repository.verify_field_review(
                page_state_id=snapshot.id,
                field_template_id=field_template_id,
                data_version=snapshot.data_version,
                value_snapshot=self._value_snapshot_for_field(
                    entry_payload=entry_payload,
                    field_row=field_row_by_id[field_template_id],
                    field_template_id=field_template_id,
                ),
                actor_user_id=actor_user_id,
                review_type=DataCaptureFieldReviewTypeChoices.DATA_REVIEW,
            )

        required_field_template_ids = self._required_field_template_ids(
            snapshot=snapshot,
            all_field_template_ids=field_template_ids,
        )
        blockers.extend(
            self.repository.find_page_verification_field_review_blockers(
                page_state_id=snapshot.id,
                data_version=snapshot.data_version,
                required_field_template_ids=required_field_template_ids,
                review_type=DataCaptureFieldReviewTypeChoices.DATA_REVIEW,
            )
        )
        if self.reconcile_read_service.has_active_blocking_query_for_page(page_state_id=snapshot.id):
            blockers.append("active_blocking_query")

        if blockers:
            return False, DataCapturePageState.UNDER_REVIEW, blockers

        page_status = self.repository.verify_page_state_if_ready(
            page_state_id=snapshot.id,
            actor_user_id=actor_user_id,
        )
        self._verify_visit_if_all_forms_verified(
            page_state_id=snapshot.id,
            subject_id=subject_id,
            visit_id=visit_id,
            actor_user_id=actor_user_id,
            page_status=page_status,
        )
        return True, page_status, []

    def is_field_verified_for_page_state(
        self,
        *,
        page_state_id: int,
        field_template_id: int,
    ) -> bool:
        return self.repository.is_field_review_verified(
            page_state_id=page_state_id,
            field_template_id=field_template_id,
            review_type=DataCaptureFieldReviewTypeChoices.DATA_REVIEW,
        )

    def _verify_visit_if_all_forms_verified(
        self,
        *,
        page_state_id: int,
        subject_id: int,
        visit_id: int,
        actor_user_id: int | None,
        page_status: str,
    ) -> None:
        if page_status != DataCapturePageState.VERIFIED:
            return
        if not self.repository.are_all_visit_forms_verified(
            subject_id=subject_id,
            visit_id=visit_id,
        ):
            return
        changed = self.subject_event_lifecycle_adapter.verify_event_instance(
            event_instance_id=visit_id,
            actor_user_id=actor_user_id,
        )
        if not changed:
            return
        self.event_transition_service.execute(
            TriggerPageStateEventTransitionCommand(
                page_state_id=page_state_id,
                actor_user_id=actor_user_id,
                trigger_source="datacapture_page_state_verified",
            )
        )

    def list_verified_or_waived_field_template_ids(
        self,
        *,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
    ) -> set[int]:
        snapshot = self.repository.get_page_state(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
        )
        if snapshot is None:
            return set()
        return self.repository.list_verified_or_waived_field_template_ids(
            page_state_id=snapshot.id,
            data_version=snapshot.data_version,
            review_type=DataCaptureFieldReviewTypeChoices.DATA_REVIEW,
        )

    def reopen_verified_page_state(
        self,
        *,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
        reason_text: str | None,
        actor_user_id: int | None = None,
    ) -> str:
        snapshot = self.repository.get_page_state(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
        )
        self.validator.require_page_state(snapshot)
        self.validator.require_reopen_status(snapshot.status)
        normalized_reason = self.validator.require_reopen_reason(reason_text)
        page_status = self.repository.reopen_verified_page_state(
            page_state_id=snapshot.id,
            reason_text=normalized_reason,
            actor_user_id=actor_user_id,
        )
        if page_status == DataCapturePageState.CORRECTION_REQUIRED:
            self.subject_event_lifecycle_adapter.mark_event_instance_in_progress(
                event_instance_id=visit_id,
                actor_user_id=actor_user_id,
            )
        return page_status

    def list_verified_field_template_ids(
        self,
        *,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
    ) -> set[int]:
        snapshot = self.repository.get_page_state(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
        )
        if snapshot is None:
            return set()
        return self.repository.list_verified_field_template_ids(
            page_state_id=snapshot.id,
            data_version=snapshot.data_version,
            review_type=DataCaptureFieldReviewTypeChoices.DATA_REVIEW,
        )


__all__ = ["DataCapturePageStateVerificationFinalDataService"]
