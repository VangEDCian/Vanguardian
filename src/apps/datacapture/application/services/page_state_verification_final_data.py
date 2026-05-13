import json

from django.core.exceptions import ValidationError

from apps.core.choices import DataCapturePageEntryStatusChoices, DataCapturePageStateStatusChoices
from apps.crf.public import CrfContextAdapter
from apps.datacapture.infrastructure.repositories import DjangoDataCapturePageRepository
from apps.subject.application.services.form_field_review_table import FormFieldReviewTableService


class DataCapturePageStateVerificationFinalDataService:
    def __init__(self, repository=None):
        self.repository = repository or DjangoDataCapturePageRepository()

    @staticmethod
    def _load_json_dict(raw_value) -> dict:
        if not raw_value or not str(raw_value).strip():
            return {}
        try:
            loaded = json.loads(raw_value)
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        return loaded if isinstance(loaded, dict) else {}

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
    def _preserve_non_form_storage(existing_final_payload: dict, field_rows: list[dict]) -> dict:
        all_form_keys = FormFieldReviewTableService.all_form_storage_keys(field_rows)
        return {
            key: value
            for key, value in existing_final_payload.items()
            if key not in all_form_keys and key != "__form_verification__"
        }

    @staticmethod
    def _merge_checked_fields_from_entry(
        *,
        base_payload: dict,
        entry_payload: dict,
        field_rows: list[dict],
        checked_set: set[int],
    ) -> dict:
        merged = dict(base_payload)
        for field_row in field_rows:
            try:
                template_id = int(field_row.get("id"))
            except (TypeError, ValueError):
                continue
            if template_id not in checked_set:
                continue
            field_key = str(field_row.get("field_key") or "").strip()
            merged.update(
                FormFieldReviewTableService.slice_payload_for_field(
                    entry_payload,
                    field_key=field_key,
                    field_template_id=template_id,
                ),
            )
        return merged

    def _get_submitted_page_state_or_raise(self, *, subject_id: int, visit_id: int, crf_template_id: int):
        snapshot = self.repository.get_page_state(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
        )
        if snapshot is None:
            raise ValidationError("No page state exists for this subject visit and form.")
        status = (snapshot.status or "").strip().lower()
        if status != DataCapturePageStateStatusChoices.SUBMITTED.value:
            raise ValidationError(
                "Verify can only be updated while the page state is submitted (not yet fully verified).",
            )
        return snapshot

    def _get_latest_submitted_entry_or_raise(self, *, subject_id: int, visit_id: int, crf_template_id: int):
        entry = self.repository.get_latest_submitted_entry(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
        )
        if entry is None or (entry.status or "").strip().lower() != DataCapturePageEntryStatusChoices.SUBMITTED.value:
            raise ValidationError("No submitted page entry exists to verify against.")
        return entry

    def merge_checked_field_template_ids(
        self,
        *,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
        checked_field_template_ids: list[int],
        actor_user_id: int | None = None,
    ) -> tuple[bool, str]:
        snapshot = self._get_submitted_page_state_or_raise(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
        )
        entry = self._get_latest_submitted_entry_or_raise(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
        )
        entry_payload = self._load_json_dict(entry.data)
        field_rows = CrfContextAdapter().list_template_fields_with_ui_config(template_id=crf_template_id)
        if not field_rows:
            raise ValidationError("No field definitions exist for this CRF template.")
        preserved_payload = self._preserve_non_form_storage(
            existing_final_payload=self._load_json_dict(snapshot.final_data),
            field_rows=field_rows,
        )
        merged = self._merge_checked_fields_from_entry(
            base_payload=preserved_payload,
            entry_payload=entry_payload,
            field_rows=field_rows,
            checked_set=self._normalize_checked_ids(checked_field_template_ids),
        )

        all_verified = FormFieldReviewTableService.all_fields_verified_against_entry(
            final_payload=merged,
            entry_payload=entry_payload,
            field_templates_payload=field_rows,
        )

        new_status = (
            DataCapturePageStateStatusChoices.VERIFIED.value
            if all_verified
            else DataCapturePageStateStatusChoices.SUBMITTED.value
        )

        final_json: str | None
        if not merged:
            final_json = None
        else:
            final_json = json.dumps(merged, ensure_ascii=False)

        self.repository.update_page_state_final_data_and_status(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
            final_data=final_json,
            status=new_status,
            actor_user_id=actor_user_id,
        )
        return all_verified, new_status


__all__ = ["DataCapturePageStateVerificationFinalDataService"]
