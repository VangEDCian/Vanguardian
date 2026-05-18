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
        raw_ids = body.get("field_template_ids")
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
            "message_text": str(body.get("message_text") or "").strip(),
        }


__all__ = ["SubjectFormVerificationRequestValidator"]
