from dataclasses import dataclass
from datetime import datetime

from apps.datacapture.infrastructure.repositories import DjangoDataCapturePageRepository


@dataclass(frozen=True)
class DataCapturePageStateAuditHistoryRecord:
    occurred_at: datetime | None
    category: str
    source: str
    field_name: str
    field_description: str
    value: str
    user_display: str
    scope: str
    action: str
    from_value: str
    to_value: str
    actor: str
    reason: str
    details: tuple[dict[str, str], ...]


class DataCapturePageStateAuditHistoryService:
    repository_class = DjangoDataCapturePageRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def list_for_subject(
        self,
        *,
        subject_id: int,
        limit: int = 200,
        search: str = "",
        field_name: str = "",
    ) -> list[dict]:
        rows = self.repository.list_page_state_transition_history_for_subject(
            subject_id=subject_id,
            limit=limit,
            search=search,
            field_name=field_name,
        )
        return [
            self._to_public_dict(
                DataCapturePageStateAuditHistoryRecord(
                    occurred_at=row["occurred_at"],
                    category="page_state",
                    source="Page State",
                    field_name=row.get("field_name") or "page_state_status",
                    field_description=row.get("field_description") or self._build_scope(row),
                    value=row.get("value") or self._build_value(row),
                    user_display=row.get("user_display") or self._format_actor(row["actor_id"]),
                    scope=self._build_scope(row),
                    action="Page state transition",
                    from_value=self._humanize_value(row["from_status"]),
                    to_value=self._humanize_value(row["to_status"]),
                    actor=self._format_actor(row["actor_id"]),
                    reason=self._format_reason(row["reason_code"], row["reason_text"]),
                    details=tuple(self._build_details(row)),
                )
            )
            for row in rows
        ]

    @classmethod
    def _build_scope(cls, row: dict) -> str:
        parts = [
            row["event_label"],
            row["form_label"],
        ]
        if row["repeat_index"] and int(row["repeat_index"]) > 1:
            parts.append(f"Repeat {row['repeat_index']}")
        return " / ".join(part for part in parts if part) or "Page State"

    @classmethod
    def _build_value(cls, row: dict) -> str:
        return " ".join(
            str(part).strip()
            for part in (
                cls._humanize_value(row["from_status"]),
                cls._humanize_value(row["to_status"]),
                row["data_version"],
                cls._format_reason(row["reason_code"], row["reason_text"]),
                cls._humanize_value(row["trigger_source"]),
            )
            if str(part or "").strip()
        )

    @classmethod
    def _build_details(cls, row: dict) -> list[dict[str, str]]:
        details = [
            ("Page State ID", row["page_state_id"]),
            ("Data Version", row["data_version"]),
            ("Trigger Source", cls._humanize_value(row["trigger_source"])),
            ("Event", row["event_code"]),
            ("Form", row["form_code"]),
        ]
        return [
            {"label": label, "value": str(value)}
            for label, value in details
            if cls._has_value(value)
        ]

    @staticmethod
    def _format_actor(actor_id) -> str:
        if actor_id is None:
            return "System"
        return f"User #{actor_id}"

    @classmethod
    def _format_reason(cls, reason_code: str | None, reason_text: str | None) -> str:
        code = cls._humanize_value(reason_code)
        text = str(reason_text or "").strip()
        if code and text:
            return f"{code}: {text}"
        return code or text

    @staticmethod
    def _humanize_value(value) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        return text.replace("_", " ").replace("-", " ").title()

    @staticmethod
    def _has_value(value) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        return True

    @staticmethod
    def _to_public_dict(record: DataCapturePageStateAuditHistoryRecord) -> dict:
        return {
            "occurred_at": record.occurred_at,
            "category": record.category,
            "source": record.source,
            "field_name": record.field_name,
            "field_description": record.field_description,
            "value": record.value,
            "user_display": record.user_display,
            "scope": record.scope,
            "action": record.action,
            "from_value": record.from_value,
            "to_value": record.to_value,
            "actor": record.actor,
            "reason": record.reason,
            "details": list(record.details),
        }


__all__ = [
    "DataCapturePageStateAuditHistoryRecord",
    "DataCapturePageStateAuditHistoryService",
]
