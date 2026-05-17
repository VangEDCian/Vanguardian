from django.db import transaction
from django.utils import timezone

from apps.crf.application.commands.upsert_crf_template import UpsertCrfTemplateCommand
from apps.crf.application.commands.upsert_section_template import UpsertSectionTemplateCommand
from apps.crf.domain.exceptions import StudyScopeViolationError
from apps.crf.infrastructure.repositories import DjangoCrfTemplateRepository


class CrfTemplateCommandService:
    repository_class = DjangoCrfTemplateRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    @staticmethod
    def _normalize_selected_study_id(selected_study_id):
        if selected_study_id is None:
            raise StudyScopeViolationError("No study is selected in the current context.")
        return int(selected_study_id)

    @classmethod
    def _ensure_current_study_scope(cls, *, selected_study_id, study_id):
        selected_study_id = cls._normalize_selected_study_id(selected_study_id)
        if int(study_id) != selected_study_id:
            raise StudyScopeViolationError("Command study scope does not match the selected study.")
        return selected_study_id

    @transaction.atomic
    def upsert_crf_template(self, command: UpsertCrfTemplateCommand, *, now=None):
        self._ensure_current_study_scope(
            selected_study_id=command.selected_study_id,
            study_id=command.study_id,
        )
        timestamp = now or timezone.now()
        defaults = {
            "deleted": False,
            "is_active": True,
            "updated_at": timestamp,
            "updated_by_id": command.actor_user_id,
        }

        crf_template = self.repository.get_template_for_upsert(
            study_id=command.study_id,
            code=command.code,
            version=command.version,
        )

        if crf_template is None:
            crf_template = self.repository.build_template(
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
        self.repository.save_template(crf_template)
        return import_outcome

    @transaction.atomic
    def upsert_section_template(self, command: UpsertSectionTemplateCommand, *, now=None):
        selected_study_id = self._normalize_selected_study_id(command.selected_study_id)
        crf_template = self.repository.get_template(template_id=command.crf_template_id)
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
            section_template = self.repository.get_section_template(
                section_template_id=command.section_template_id,
                crf_template_id=command.crf_template_id,
            )

        if section_template is None:
            section_template = self.repository.build_section_template(
                crf_template_id=command.crf_template_id,
                section_code=command.section_code,
                created_at=timestamp,
                created_by_id=command.actor_user_id,
                **defaults,
            )
        else:
            for field_name, value in defaults.items():
                setattr(section_template, field_name, value)

        self._set_translated_value(section_template, "section_name", "vi", command.vi_name)
        self._set_translated_value(section_template, "section_name", "en", command.en_name)
        self._set_translated_value(section_template, "description", "vi", command.vi_description)
        self._set_translated_value(section_template, "description", "en", command.en_description)
        self._set_translated_value(section_template, "help_text", "vi", command.vi_help_text)
        self._set_translated_value(section_template, "help_text", "en", command.en_help_text)
        self._set_translated_value(section_template, "instruction_text", "vi", command.vi_instruction_text)
        self._set_translated_value(section_template, "instruction_text", "en", command.en_instruction_text)
        self.repository.save_section_template(section_template)
        return section_template

    @staticmethod
    def _set_translated_value(instance, field_name, language_code, value):
        instance.set_current_language(language_code, initialize=True)
        setattr(instance, field_name, value)


__all__ = ["CrfTemplateCommandService"]
