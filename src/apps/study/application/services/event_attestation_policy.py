from dataclasses import dataclass

from django.db import OperationalError, ProgrammingError

from apps.study.infrastructure.persistence.models import EventAttestationPolicy


@dataclass(frozen=True)
class EventAttestationPolicySnapshot:
    id: int
    study_id: int
    study_version: str
    event_definition_id: int
    code: str
    action_kind: str
    display_order: int
    statement_code: str
    statement_version: str
    required_permission_code: str
    required_role_code: str
    delegation_task_code: str
    gate_code: str
    requires_confirmation_checkbox: bool
    requires_signature: bool
    requires_reauthentication: bool
    invalidate_on_data_change: bool
    invalidate_on_scope_change: bool
    is_required_for_lock: bool
    dialog_title: str
    action_label: str
    statement_text: str
    confirmation_label: str
    success_message: str


class StudyEventAttestationPolicyReader:
    def list_enabled_for_event(
        self,
        *,
        study_id: int,
        study_version: str,
        event_definition_id: int,
        language_code: str | None = None,
    ) -> list[EventAttestationPolicySnapshot]:
        language = self._normalize_language(language_code)
        try:
            policies = (
                EventAttestationPolicy.objects.filter(
                    study_id=study_id,
                    study_version=study_version,
                    event_definition_id=event_definition_id,
                    is_enabled=True,
                    deleted=False,
                )
                .prefetch_related("translations")
                .order_by("display_order", "id")
            )
            return [self._to_snapshot(policy, language_code=language) for policy in policies]
        except (OperationalError, ProgrammingError):
            return []

    @staticmethod
    def _normalize_language(language_code: str | None) -> str:
        raw = str(language_code or "").strip().lower()
        if not raw:
            return "en"
        return raw.split("-", maxsplit=1)[0]

    @classmethod
    def _translation_for(cls, policy, *, language_code: str):
        translations = list(getattr(policy, "translations", []).all())
        if not translations:
            return None
        by_language = {
            cls._normalize_language(getattr(item, "language_code", "")): item
            for item in translations
        }
        return by_language.get(language_code) or by_language.get("en") or translations[0]

    @classmethod
    def _to_snapshot(cls, policy, *, language_code: str) -> EventAttestationPolicySnapshot:
        translation = cls._translation_for(policy, language_code=language_code)
        return EventAttestationPolicySnapshot(
            id=int(policy.pk),
            study_id=int(policy.study_id),
            study_version=str(policy.study_version or ""),
            event_definition_id=int(policy.event_definition_id),
            code=str(policy.code or ""),
            action_kind=str(policy.action_kind or ""),
            display_order=int(policy.display_order or 0),
            statement_code=str(policy.statement_code or ""),
            statement_version=str(policy.statement_version or ""),
            required_permission_code=str(policy.required_permission_code or ""),
            required_role_code=str(policy.required_role_code or ""),
            delegation_task_code=str(policy.delegation_task_code or ""),
            gate_code=str(policy.gate_code or ""),
            requires_confirmation_checkbox=bool(policy.requires_confirmation_checkbox),
            requires_signature=bool(policy.requires_signature),
            requires_reauthentication=bool(policy.requires_reauthentication),
            invalidate_on_data_change=bool(policy.invalidate_on_data_change),
            invalidate_on_scope_change=bool(policy.invalidate_on_scope_change),
            is_required_for_lock=bool(policy.is_required_for_lock),
            dialog_title=str(getattr(translation, "dialog_title", "") or policy.code or ""),
            action_label=str(getattr(translation, "action_label", "") or policy.code or ""),
            statement_text=str(getattr(translation, "statement_text", "") or ""),
            confirmation_label=str(getattr(translation, "confirmation_label", "") or ""),
            success_message=str(getattr(translation, "success_message", "") or ""),
        )


__all__ = [
    "EventAttestationPolicySnapshot",
    "StudyEventAttestationPolicyReader",
]
