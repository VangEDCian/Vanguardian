import json

from apps.subject.application.exceptions import (
    SubjectFormVerificationFieldTemplateIdsTypeError,
    SubjectFormVerificationFieldTemplateIdsValueError,
    SubjectFormVerificationInvalidJsonError,
)


class SubjectFormVerificationRequestValidator:
    """Reusable request validation for form verification use cases."""

    @staticmethod
    def _parse_json_body(raw_body: bytes | str) -> dict:
        try:
            if isinstance(raw_body, bytes):
                raw_body = raw_body.decode("utf-8")
            body = json.loads(raw_body or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SubjectFormVerificationInvalidJsonError() from exc
        if not isinstance(body, dict):
            raise SubjectFormVerificationInvalidJsonError()
        return body

    @classmethod
    def parse_checked_field_template_ids(cls, raw_body: bytes | str) -> list[int]:
        body = cls._parse_json_body(raw_body)
        return cls._normalize_field_template_ids(body.get("field_template_ids"))

    @classmethod
    def parse_verify_checked_payload(cls, raw_body: bytes | str) -> dict[str, object]:
        body = cls._parse_json_body(raw_body)
        return {
            "field_template_ids": cls._normalize_field_template_ids(body.get("field_template_ids")),
            "reason_text": str(body.get("reason_text") or "").strip(),
            "review_page_entry_id": str(body.get("review_page_entry_id") or "").strip(),
            "review_entry_version": str(body.get("review_entry_version") or "").strip(),
            "review_page_status": str(body.get("review_page_status") or "").strip(),
        }

    @staticmethod
    def _normalize_field_template_ids(raw_ids) -> list[int]:
        if raw_ids is None:
            return []
        if not isinstance(raw_ids, list):
            raise SubjectFormVerificationFieldTemplateIdsTypeError()

        normalized: list[int] = []
        for item in raw_ids:
            try:
                normalized.append(int(item))
            except (TypeError, ValueError) as exc:
                raise SubjectFormVerificationFieldTemplateIdsValueError() from exc
        return normalized

    @classmethod
    def parse_reopen_reason_text(cls, raw_body: bytes | str) -> str:
        body = cls._parse_json_body(raw_body)
        return str(body.get("reason_text") or "").strip()

    @classmethod
    def parse_query_thread_action(cls, raw_body: bytes | str) -> dict[str, object]:
        body = cls._parse_json_body(raw_body)
        try:
            dataquery_id = int(body.get("dataquery_id"))
            field_template_id = int(body.get("field_template_id"))
        except (TypeError, ValueError) as exc:
            raise SubjectFormVerificationFieldTemplateIdsValueError() from exc
        return {
            "dataquery_id": dataquery_id,
            "field_template_id": field_template_id,
            "message_text": str(body.get("message_text") or "").strip(),
            "close_query": body.get("close_query") is True,
            "cancel_query": body.get("cancel_query") is True,
            "is_resolved": body.get("is_resolved") is True,
        }

    @classmethod
    def parse_open_query_action(cls, raw_body: bytes | str) -> dict[str, object]:
        body = cls._parse_json_body(raw_body)
        try:
            field_template_id = int(body.get("field_template_id"))
        except (TypeError, ValueError) as exc:
            raise SubjectFormVerificationFieldTemplateIdsValueError() from exc
        return {
            "field_template_id": field_template_id,
            "field_key": str(body.get("field_key") or "").strip(),
            "message_text": str(body.get("message_text") or "").strip(),
        }


__all__ = ["SubjectFormVerificationRequestValidator"]
