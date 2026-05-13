import json

from django.core.exceptions import ValidationError

from apps.core.choices import DataCapturePageEntryStatusChoices, DataCapturePageStateStatusChoices
from apps.crf.public import CrfContextAdapter
from apps.datacapture.infrastructure.repositories import DjangoDataCapturePageRepository
from apps.subject.application.services.form_field_review_table import FormFieldReviewTableService


class DataCapturePageStateVerificationFinalDataService:
    def __init__(self, repository=None):
        self.repository = repository or DjangoDataCapturePageRepository()

    def merge_checked_field_template_ids(
        self,
        *,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
        checked_field_template_ids: list[int],
        actor_user_id: int | None = None,
    ) -> tuple[bool, str]:
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

        entry = self.repository.get_latest_submitted_entry(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
        )
        if entry is None or (entry.status or "").strip().lower() != DataCapturePageEntryStatusChoices.SUBMITTED.value:
            raise ValidationError("No submitted page entry exists to verify against.")

        try:
            entry_payload = json.loads(entry.data or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            entry_payload = {}
        if not isinstance(entry_payload, dict):
            entry_payload = {}

        field_rows = CrfContextAdapter().list_template_fields_with_ui_config(template_id=crf_template_id)
        if not field_rows:
            raise ValidationError("No field definitions exist for this CRF template.")

        all_form_keys = FormFieldReviewTableService.all_form_storage_keys(field_rows)

        existing: dict = {}
        raw_final = snapshot.final_data
        if raw_final and str(raw_final).strip():
            try:
                loaded = json.loads(raw_final)
            except (TypeError, ValueError, json.JSONDecodeError):
                loaded = {}
            if isinstance(loaded, dict):
                existing = loaded

        merged: dict = {
            k: v
            for k, v in existing.items()
            if k not in all_form_keys and k != "__form_verification__"
        }

        checked_set: set[int] = set()
        for x in checked_field_template_ids or []:
            try:
                checked_set.add(int(x))
            except (TypeError, ValueError):
                continue

        for field_row in field_rows:
            try:
                tid = int(field_row.get("id"))
            except (TypeError, ValueError):
                continue
            if tid not in checked_set:
                continue
            fk = str(field_row.get("field_key") or "").strip()
            piece = FormFieldReviewTableService.slice_payload_for_field(
                entry_payload,
                field_key=fk,
                field_template_id=tid,
            )
            merged.update(piece)

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
