from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.crf.domain.exceptions import StudyScopeViolationError
from apps.crf.models import CrfSectionTemplate, CrfTemplate
from apps.shared.context_processors import StudyDropdownHandler


@dataclass(frozen=True)
class UpsertCrfTemplateCommand:
    study_id: int
    code: str
    version: str
    vi_name: str
    en_name: str
    actor_user_id: int


@dataclass(frozen=True)
class UpsertSectionTemplateCommand:
    crf_template_id: int
    section_template_id: int | None
    section_code: str
    vi_name: str
    en_name: str
    vi_description: str
    en_description: str
    vi_help_text: str
    en_help_text: str
    vi_instruction_text: str
    en_instruction_text: str
    display_order: int
    is_required: bool
    is_repeatable: bool
    min_repeats: int
    max_repeats: int | None
    actor_user_id: int


class CrfTemplateCommandService:
    template_model = CrfTemplate
    section_template_model = CrfSectionTemplate

    @staticmethod
    def _resolve_selected_study_id(request):
        try:
            selected_study_id = StudyDropdownHandler(request=request).build().selected_id
        except Exception as exc:
            raise StudyScopeViolationError("No study is selected in the current context.") from exc
        if selected_study_id is None:
            raise StudyScopeViolationError("No study is selected in the current context.")
        return int(selected_study_id)

    @classmethod
    def _ensure_current_study_scope(cls, *, request, study_id):
        selected_study_id = cls._resolve_selected_study_id(request)
        if int(study_id) != selected_study_id:
            raise StudyScopeViolationError("Command study scope does not match the selected study.")
        return selected_study_id

    @transaction.atomic
    def upsert_crf_template(self, command: UpsertCrfTemplateCommand, *, request, now=None):
        self._ensure_current_study_scope(request=request, study_id=command.study_id)
        timestamp = now or timezone.now()
        defaults = {
            "deleted": False,
            "is_active": True,
            "updated_at": timestamp,
            "updated_by_id": command.actor_user_id,
        }

        crf_template = self.template_model.objects.filter(
            study_id=command.study_id,
            code=command.code,
            version=command.version,
        ).first()

        if crf_template is None:
            crf_template = self.template_model(
                study_id=command.study_id,
                code=command.code,
                version=command.version,
                created_at=timestamp,
                created_by_id=command.actor_user_id,
                **defaults,
            )
            import_outcome = "created"
        else:
            for field_name, value in defaults.items():
                setattr(crf_template, field_name, value)
            import_outcome = "updated"

        self._set_translated_value(crf_template, "name", "vi", command.vi_name)
        self._set_translated_value(crf_template, "name", "en", command.en_name)
        crf_template.save()
        return import_outcome

    @transaction.atomic
    def upsert_section_template(self, command: UpsertSectionTemplateCommand, *, request, now=None):
        selected_study_id = self._resolve_selected_study_id(request)
        crf_template = self.template_model.objects.filter(
            pk=command.crf_template_id,
            deleted=False,
        ).first()
        if crf_template is None:
            raise StudyScopeViolationError("CRF template is not found in the selected study scope.")
        if int(crf_template.study_id) != selected_study_id:
            raise StudyScopeViolationError("Section template command cannot modify another study.")

        timestamp = now or timezone.now()
        defaults = {
            "deleted": False,
            "display_order": command.display_order,
            "is_required": command.is_required,
            "is_enabled": True,
            "is_repeatable": command.is_repeatable,
            "min_repeats": command.min_repeats,
            "max_repeats": command.max_repeats,
            "updated_at": timestamp,
            "updated_by_id": command.actor_user_id,
        }

        section_template = None
        if command.section_template_id:
            section_template = self.section_template_model.objects.filter(
                pk=command.section_template_id,
                crf_template_id=command.crf_template_id,
            ).first()

        if section_template is None:
            section_template = self.section_template_model(
                crf_template_id=command.crf_template_id,
                section_code=command.section_code,
                created_at=timestamp,
                created_by_id=command.actor_user_id,
                **defaults,
            )
            import_outcome = "created"
        else:
            for field_name, value in defaults.items():
                setattr(section_template, field_name, value)
            import_outcome = "updated"

        self._set_translated_value(section_template, "section_name", "vi", command.vi_name)
        self._set_translated_value(section_template, "section_name", "en", command.en_name)
        self._set_translated_value(section_template, "description", "vi", command.vi_description)
        self._set_translated_value(section_template, "description", "en", command.en_description)
        self._set_translated_value(section_template, "help_text", "vi", command.vi_help_text)
        self._set_translated_value(section_template, "help_text", "en", command.en_help_text)
        self._set_translated_value(section_template, "instruction_text", "vi", command.vi_instruction_text)
        self._set_translated_value(section_template, "instruction_text", "en", command.en_instruction_text)
        section_template.save()
        return section_template

    @staticmethod
    def _set_translated_value(instance, field_name, language_code, value):
        instance.set_current_language(language_code, initialize=True)
        setattr(instance, field_name, value)
