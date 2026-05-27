from apps.study.application import (
    CommitRandomizationImportCommand,
    CreateStudyCommand,
    DeleteRandomizationArmCommand,
    DeleteRandomizationSchemeCommand,
    DeleteSiteCommand,
    DeleteStudyCommand,
    ImportStudyCrfSectionLayoutConfigsTemplateCommand,
    ImportStudyCrfTemplateFieldsTemplateCommand,
    ImportStudyCrfTemplatesTemplateCommand,
    ImportStudyCrfValidationRulesTemplateCommand,
    ImportStudyEventDefinitionsTemplateCommand,
    ImportStudyEventFormBindingsTemplateCommand,
    ImportStudyFactMappingsTemplateCommand,
    PreviewRandomizationImportCommand,
    ToggleStudyStatusCommand,
    UpdateSiteCommand,
    UpdateStudyCommand,
)
from apps.study.application.commands.site_data import CreateSiteCommand


def to_import_study_crf_templates_template_command(**kwargs) -> ImportStudyCrfTemplatesTemplateCommand:
    return ImportStudyCrfTemplatesTemplateCommand(**kwargs)


def to_import_study_crf_template_fields_template_command(**kwargs) -> ImportStudyCrfTemplateFieldsTemplateCommand:
    return ImportStudyCrfTemplateFieldsTemplateCommand(**kwargs)


def to_import_study_crf_section_layout_configs_template_command(
    **kwargs,
) -> ImportStudyCrfSectionLayoutConfigsTemplateCommand:
    return ImportStudyCrfSectionLayoutConfigsTemplateCommand(**kwargs)


def to_import_study_crf_validation_rules_template_command(
    **kwargs,
) -> ImportStudyCrfValidationRulesTemplateCommand:
    return ImportStudyCrfValidationRulesTemplateCommand(**kwargs)


def to_import_study_event_definitions_template_command(**kwargs) -> ImportStudyEventDefinitionsTemplateCommand:
    return ImportStudyEventDefinitionsTemplateCommand(**kwargs)


def to_import_study_event_form_bindings_template_command(**kwargs) -> ImportStudyEventFormBindingsTemplateCommand:
    return ImportStudyEventFormBindingsTemplateCommand(**kwargs)


def to_import_study_fact_mappings_template_command(**kwargs) -> ImportStudyFactMappingsTemplateCommand:
    return ImportStudyFactMappingsTemplateCommand(**kwargs)


def to_preview_randomization_import_command(**kwargs) -> PreviewRandomizationImportCommand:
    return PreviewRandomizationImportCommand(**kwargs)


def to_commit_randomization_import_command(**kwargs) -> CommitRandomizationImportCommand:
    return CommitRandomizationImportCommand(**kwargs)


def to_delete_randomization_scheme_command(**kwargs) -> DeleteRandomizationSchemeCommand:
    return DeleteRandomizationSchemeCommand(**kwargs)


def to_delete_randomization_arm_command(**kwargs) -> DeleteRandomizationArmCommand:
    return DeleteRandomizationArmCommand(**kwargs)


def to_create_site_command(**kwargs) -> CreateSiteCommand:
    return CreateSiteCommand(**kwargs)


def to_update_site_command(**kwargs) -> UpdateSiteCommand:
    return UpdateSiteCommand(**kwargs)


def to_delete_site_command(**kwargs) -> DeleteSiteCommand:
    return DeleteSiteCommand(**kwargs)


def to_create_study_command(**kwargs) -> CreateStudyCommand:
    return CreateStudyCommand(**kwargs)


def to_update_study_command(**kwargs) -> UpdateStudyCommand:
    return UpdateStudyCommand(**kwargs)


def to_toggle_study_status_command(**kwargs) -> ToggleStudyStatusCommand:
    return ToggleStudyStatusCommand(**kwargs)


def to_delete_study_command(**kwargs) -> DeleteStudyCommand:
    return DeleteStudyCommand(**kwargs)


__all__ = [
    "to_import_study_crf_template_fields_template_command",
    "to_import_study_crf_validation_rules_template_command",
    "to_import_study_crf_section_layout_configs_template_command",
    "to_import_study_crf_templates_template_command",
    "to_import_study_event_definitions_template_command",
    "to_import_study_event_form_bindings_template_command",
    "to_import_study_fact_mappings_template_command",
    "to_preview_randomization_import_command",
    "to_commit_randomization_import_command",
    "to_delete_randomization_scheme_command",
    "to_delete_randomization_arm_command",
    "to_create_site_command",
    "to_update_site_command",
    "to_delete_site_command",
    "to_create_study_command",
    "to_update_study_command",
    "to_toggle_study_status_command",
    "to_delete_study_command",
]
