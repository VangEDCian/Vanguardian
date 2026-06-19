from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from django.db import transaction

from apps.audit.public import AuditContextAdapter
from apps.crf.public import CrfContextAdapter
from apps.shared.constants import AuditEventActionEnum, AuditEventObjectTypeEnum
from apps.study.infrastructure.repositories.event_form_display_label import (
    DjangoEventFormDisplayLabelRepository,
)

TOKEN_RE = re.compile(r"{{\s*([^{}]+?)\s*}}")
FIELD_TOKEN_PREFIX = "field:"
SUPPORTED_LANGUAGE_CODES = ("vi", "en")


@dataclass(frozen=True)
class EventFormDisplayTemplateValidationError:
    code: str
    message: str
    token: str | None = None


@dataclass(frozen=True)
class EventFormDisplayTemplatePreview:
    language_code: str
    label: str
    fallback_label: str
    errors: tuple[EventFormDisplayTemplateValidationError, ...]


@dataclass(frozen=True)
class EventFormDisplayTranslationSnapshot:
    language_code: str
    label_template: str
    fallback_template: str
    empty_value_text: str


@dataclass(frozen=True)
class EventFormDisplayConfigSnapshot:
    binding_id: int
    template_id: int
    form_code: str
    form_name_by_language: dict[str, str]
    is_enabled: bool
    syntax_version: int
    max_length: int
    use_choice_display_label: bool
    empty_value_policy: str
    translations: dict[str, EventFormDisplayTranslationSnapshot]


class EventFormDisplayLabelValidationError(ValueError):
    def __init__(self, errors: list[EventFormDisplayTemplateValidationError]):
        self.errors = tuple(errors)
        super().__init__("Invalid event form display label configuration.")


class EventFormDisplayLabelService:
    crf_context_adapter_class = CrfContextAdapter
    audit_context_adapter_class = AuditContextAdapter
    repository_class = DjangoEventFormDisplayLabelRepository

    def __init__(self, *, crf_context_adapter=None, audit_context_adapter=None, repository=None):
        self.crf_context_adapter = crf_context_adapter or self.crf_context_adapter_class()
        self.audit_context_adapter = audit_context_adapter or self.audit_context_adapter_class()
        self.repository = repository or self.repository_class()

    def get_config(self, *, binding_id: int) -> EventFormDisplayConfigSnapshot | None:
        binding = self._get_binding(binding_id=binding_id)
        if binding is None:
            return None
        return self._build_snapshot(binding)

    def get_binding_snapshot(self, *, binding_id: int):
        return self.repository.get_binding_snapshot(binding_id=binding_id)

    def list_binding_choices(self, *, study_id: int) -> list[dict[str, Any]]:
        bindings = (
            self.repository.list_bindings(study_id=study_id)
        )
        payload: list[dict[str, Any]] = []
        for binding in bindings:
            payload.append(
                {
                    "binding_id": int(binding.pk),
                    "event_code": binding.event_definition.code,
                    "event_name": binding.event_definition.name,
                    "form_code": binding.form_definition.code,
                    "form_name_vi": self._resolve_form_name(binding, "vi"),
                    "form_name_en": self._resolve_form_name(binding, "en"),
                    "is_repeatable_within_event": bool(binding.is_repeatable_within_event),
                    "has_config": hasattr(binding, "display_config"),
                }
            )
        return payload

    def preview(
        self,
        *,
        binding_id: int,
        language_code: str,
        label_template: str,
        fallback_template: str,
        empty_value_text: str,
        empty_value_policy: str,
        max_length: int,
        repeat_index: int,
        field_values: dict[str, Any],
    ) -> EventFormDisplayTemplatePreview:
        binding = self._get_binding(binding_id=binding_id)
        if binding is None:
            raise ValueError("Event form binding was not found.")
        allowed_field_keys = self._allowed_field_keys(template_id=binding.form_definition_id)
        errors = self._validate_templates(
            label_template=label_template,
            fallback_template=fallback_template,
            allowed_field_keys=allowed_field_keys,
            max_length=max_length,
        )
        render_context = self._build_render_context(
            binding=binding,
            repeat_index=repeat_index,
            language_code=language_code,
            field_values=field_values,
        )
        label = ""
        fallback_label = ""
        if not errors:
            label = self._render_template(
                template=label_template,
                fallback_template=fallback_template,
                empty_value_text=empty_value_text,
                empty_value_policy=empty_value_policy,
                max_length=max_length,
                context=render_context,
            )
            fallback_label = self._render_template(
                template=fallback_template,
                fallback_template=fallback_template,
                empty_value_text=empty_value_text,
                empty_value_policy="OMIT_TOKEN",
                max_length=max_length,
                context=render_context,
            )
        return EventFormDisplayTemplatePreview(
            language_code=language_code,
            label=label,
            fallback_label=fallback_label,
            errors=tuple(errors),
        )

    @transaction.atomic
    def save_config(
        self,
        *,
        binding_id: int,
        actor_user_id: int | None,
        is_enabled: bool,
        max_length: int,
        use_choice_display_label: bool,
        empty_value_policy: str,
        translations: dict[str, dict[str, str]],
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> EventFormDisplayConfigSnapshot:
        binding = self._get_binding(binding_id=binding_id)
        if binding is None:
            raise ValueError("Event form binding was not found.")
        normalized_max_length = int(max_length)
        allowed_field_keys = self._allowed_field_keys(template_id=binding.form_definition_id)
        errors: list[EventFormDisplayTemplateValidationError] = []
        if normalized_max_length < 20 or normalized_max_length > 255:
            errors.append(
                EventFormDisplayTemplateValidationError(
                    code="max_length_out_of_range",
                    message="Max length must be between 20 and 255.",
                )
            )
        for language_code in SUPPORTED_LANGUAGE_CODES:
            translation = translations.get(language_code) or {}
            errors.extend(
                self._validate_templates(
                    label_template=str(translation.get("label_template") or ""),
                    fallback_template=str(translation.get("fallback_template") or ""),
                    allowed_field_keys=allowed_field_keys,
                    max_length=normalized_max_length,
                )
            )
        if errors:
            raise EventFormDisplayLabelValidationError(errors)

        existing = self.repository.get_active_config(binding_id=binding_id)
        before_data = self._serialize_snapshot(existing, binding) if existing is not None else {}
        now = binding.updated_at
        if existing is None:
            config = self.repository.create_config(
                created_at=now,
                updated_at=now,
                deleted=False,
                event_form_binding=binding,
                syntax_version=1,
                is_enabled=is_enabled,
                max_length=normalized_max_length,
                use_choice_display_label=use_choice_display_label,
                empty_value_policy=empty_value_policy,
                created_by_id=actor_user_id,
                updated_by_id=actor_user_id,
            )
        else:
            existing.is_enabled = is_enabled
            existing.max_length = normalized_max_length
            existing.use_choice_display_label = use_choice_display_label
            existing.empty_value_policy = empty_value_policy
            existing.updated_at = now
            existing.updated_by_id = actor_user_id
            existing.deleted = False
            config = self.repository.save_config(
                existing,
                update_fields=[
                    "is_enabled",
                    "max_length",
                    "use_choice_display_label",
                    "empty_value_policy",
                    "updated_at",
                    "updated_by_id",
                    "deleted",
                ],
            )

        for language_code in SUPPORTED_LANGUAGE_CODES:
            translation_input = translations.get(language_code) or {}
            self.repository.upsert_translation(
                config=config,
                language_code=language_code,
                payload={
                    "label_template": str(translation_input.get("label_template") or "").strip(),
                    "fallback_template": str(translation_input.get("fallback_template") or "").strip(),
                    "empty_value_text": str(translation_input.get("empty_value_text") or "").strip() or None,
                },
            )

        snapshot = self._build_snapshot(binding)
        self.audit_context_adapter.record_event(
            action=AuditEventActionEnum.STUDY_EVENT_FORM_DISPLAY_CONFIG_SAVED,
            object_type=AuditEventObjectTypeEnum.STUDY_EVENT_FORM_DISPLAY_CONFIG,
            object_id=str(binding_id),
            before_data=before_data,
            after_data=self._snapshot_to_dict(snapshot),
            actor_user_id=actor_user_id,
            ip_address=ip_address,
            user_agent=user_agent or "",
        )
        return snapshot

    def render_label(
        self,
        *,
        binding_id: int,
        language_code: str,
        repeat_index: int,
        field_values: dict[str, Any],
    ) -> str:
        binding = self._get_binding(binding_id=binding_id)
        if binding is None:
            return ""
        snapshot = self._build_snapshot(binding)
        translation = self._resolve_translation(snapshot, language_code)
        render_context = self._build_render_context(
            binding=binding,
            repeat_index=repeat_index,
            language_code=language_code,
            field_values=field_values,
        )
        if snapshot.is_enabled and translation is not None:
            label = self._render_template(
                template=translation.label_template,
                fallback_template=translation.fallback_template,
                empty_value_text=translation.empty_value_text,
                empty_value_policy=snapshot.empty_value_policy,
                max_length=snapshot.max_length,
                context=render_context,
            )
            if label:
                return label
        return self._fallback_form_label(
            form_name=render_context["form_name"],
            repeat_index=repeat_index,
        )

    def _get_binding(self, *, binding_id: int):
        return self.repository.get_binding(binding_id=binding_id)

    def _allowed_field_keys(self, *, template_id: int) -> set[str]:
        return {
            str(field["field_key"])
            for field in self.crf_context_adapter.list_template_fields_with_ui_config(
                template_id=template_id,
            )
        }

    def _build_snapshot(self, binding) -> EventFormDisplayConfigSnapshot:
        config = getattr(binding, "display_config", None)
        translations: dict[str, EventFormDisplayTranslationSnapshot] = {}
        if config is not None and not config.deleted:
            for translation in config.translations.all():
                translations[translation.language_code] = EventFormDisplayTranslationSnapshot(
                    language_code=translation.language_code,
                    label_template=translation.label_template,
                    fallback_template=translation.fallback_template,
                    empty_value_text=translation.empty_value_text or "",
                )
        return EventFormDisplayConfigSnapshot(
            binding_id=int(binding.pk),
            template_id=int(binding.form_definition_id),
            form_code=binding.form_definition.code,
            form_name_by_language={
                "vi": self._resolve_form_name(binding, "vi"),
                "en": self._resolve_form_name(binding, "en"),
            },
            is_enabled=bool(config.is_enabled) if config is not None else False,
            syntax_version=int(config.syntax_version) if config is not None else 1,
            max_length=int(config.max_length) if config is not None else 120,
            use_choice_display_label=bool(config.use_choice_display_label) if config is not None else True,
            empty_value_policy=(
                config.empty_value_policy if config is not None else "FALLBACK"
            ),
            translations=translations,
        )

    def _serialize_snapshot(self, config, binding) -> dict[str, Any]:
        if config is None:
            return {}
        snapshot = self._build_snapshot(binding)
        return self._snapshot_to_dict(snapshot)

    @staticmethod
    def _snapshot_to_dict(snapshot: EventFormDisplayConfigSnapshot) -> dict[str, Any]:
        return {
            "binding_id": snapshot.binding_id,
            "template_id": snapshot.template_id,
            "form_code": snapshot.form_code,
            "form_name_by_language": snapshot.form_name_by_language,
            "is_enabled": snapshot.is_enabled,
            "syntax_version": snapshot.syntax_version,
            "max_length": snapshot.max_length,
            "use_choice_display_label": snapshot.use_choice_display_label,
            "empty_value_policy": snapshot.empty_value_policy,
            "translations": {
                language_code: {
                    "label_template": translation.label_template,
                    "fallback_template": translation.fallback_template,
                    "empty_value_text": translation.empty_value_text,
                }
                for language_code, translation in snapshot.translations.items()
            },
        }

    @staticmethod
    def _validate_templates(
        *,
        label_template: str,
        fallback_template: str,
        allowed_field_keys: set[str],
        max_length: int,
    ) -> list[EventFormDisplayTemplateValidationError]:
        errors: list[EventFormDisplayTemplateValidationError] = []
        for field_name, template in (
            ("label_template", label_template),
            ("fallback_template", fallback_template),
        ):
            normalized_template = str(template or "").strip()
            if not normalized_template:
                errors.append(
                    EventFormDisplayTemplateValidationError(
                        code=f"{field_name}_required",
                        message=f"{field_name} is required.",
                    )
                )
                continue
            if len(normalized_template) > 500:
                errors.append(
                    EventFormDisplayTemplateValidationError(
                        code=f"{field_name}_too_long",
                        message=f"{field_name} exceeds the 500 character limit.",
                    )
                )
            for raw_token in TOKEN_RE.findall(normalized_template):
                token = raw_token.strip()
                if token in {"form_name", "form_code", "repeat_index"}:
                    continue
                if token.startswith(FIELD_TOKEN_PREFIX):
                    field_key = token[len(FIELD_TOKEN_PREFIX):].strip()
                    if not field_key:
                        errors.append(
                            EventFormDisplayTemplateValidationError(
                                code="field_token_missing_key",
                                message="Field token must include a field key.",
                                token=token,
                            )
                        )
                    elif field_key not in allowed_field_keys:
                        errors.append(
                            EventFormDisplayTemplateValidationError(
                                code="field_key_not_found",
                                message=f"Field key '{field_key}' does not belong to the bound CRF template.",
                                token=token,
                            )
                        )
                    continue
                errors.append(
                    EventFormDisplayTemplateValidationError(
                        code="unsupported_token",
                        message=f"Unsupported token '{token}'.",
                        token=token,
                    )
                )
        if max_length < 20 or max_length > 255:
            errors.append(
                EventFormDisplayTemplateValidationError(
                    code="max_length_out_of_range",
                    message="Max length must be between 20 and 255.",
                )
            )
        return errors

    def _build_render_context(
        self,
        *,
        binding,
        repeat_index: int,
        language_code: str,
        field_values: dict[str, Any],
    ) -> dict[str, Any]:
        normalized_language = self._normalize_language_code(language_code)
        return {
            "form_name": self._resolve_form_name(binding, normalized_language),
            "form_code": binding.form_definition.code,
            "repeat_index": int(repeat_index),
            "field_values": {
                str(key): "" if value is None else str(value)
                for key, value in (field_values or {}).items()
            },
        }

    @staticmethod
    def _normalize_language_code(language_code: str | None) -> str:
        normalized = (language_code or "en").strip().lower()
        return normalized.split("-", 1)[0]

    def _resolve_form_name(self, binding, language_code: str) -> str:
        form_definition = binding.form_definition
        current = self._normalize_language_code(language_code)
        if hasattr(form_definition, "safe_translation_getter"):
            value = form_definition.safe_translation_getter(
                "name",
                default=form_definition.code,
                language_code=current,
                any_language=True,
            )
            return str(value or form_definition.code)
        return str(form_definition.code)

    def _resolve_translation(
        self,
        snapshot: EventFormDisplayConfigSnapshot,
        language_code: str,
    ) -> EventFormDisplayTranslationSnapshot | None:
        requested = self._normalize_language_code(language_code)
        if requested in snapshot.translations:
            return snapshot.translations[requested]
        if "en" in snapshot.translations:
            return snapshot.translations["en"]
        if snapshot.translations:
            return next(iter(snapshot.translations.values()))
        return None

    def _render_template(
        self,
        *,
        template: str,
        fallback_template: str,
        empty_value_text: str,
        empty_value_policy: str,
        max_length: int,
        context: dict[str, Any],
    ) -> str:
        all_field_tokens_empty = True

        def replace(match: re.Match[str]) -> str:
            nonlocal all_field_tokens_empty
            token = match.group(1).strip()
            if token == "form_name":
                return str(context["form_name"])
            if token == "form_code":
                return str(context["form_code"])
            if token == "repeat_index":
                return str(context["repeat_index"])
            if token.startswith(FIELD_TOKEN_PREFIX):
                field_key = token[len(FIELD_TOKEN_PREFIX):].strip()
                raw_value = str(context["field_values"].get(field_key, "") or "").strip()
                if raw_value:
                    all_field_tokens_empty = False
                    return raw_value
                if empty_value_policy == "EMPTY_TEXT":
                    return str(empty_value_text or "").strip()
                return ""
            return ""

        rendered = TOKEN_RE.sub(replace, str(template or ""))
        rendered = self._cleanup_rendered_text(rendered)
        should_use_fallback = not rendered or (
            all_field_tokens_empty and empty_value_policy in {"FALLBACK", "OMIT_TOKEN"}
        )
        if should_use_fallback:
            fallback = TOKEN_RE.sub(replace, str(fallback_template or ""))
            rendered = self._cleanup_rendered_text(fallback)
        if len(rendered) > max_length:
            rendered = rendered[:max_length].rstrip()
        return rendered

    @staticmethod
    def _cleanup_rendered_text(value: str) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        text = re.sub(r"\s*([:|,/])\s*", r" \1 ", text)
        text = re.sub(r"\s*[—-]\s*", " — ", text)
        text = re.sub(r"(?:\s+[—,:/|]\s+){2,}", " — ", text)
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"^[—,:/|.\s-]+", "", text)
        text = re.sub(r"[—,:/|.\s-]+$", "", text)
        return text.strip()

    @staticmethod
    def _fallback_form_label(*, form_name: str, repeat_index: int) -> str:
        return f"{form_name} #{int(repeat_index)}".strip()


def serialize_event_form_display_errors(
    exc: EventFormDisplayLabelValidationError,
) -> list[dict[str, str]]:
    return [
        {
            "code": error.code,
            "message": error.message,
            "token": error.token or "",
        }
        for error in exc.errors
    ]


__all__ = [
    "EventFormDisplayConfigSnapshot",
    "EventFormDisplayLabelService",
    "EventFormDisplayLabelValidationError",
    "EventFormDisplayTemplatePreview",
    "EventFormDisplayTemplateValidationError",
    "serialize_event_form_display_errors",
]
