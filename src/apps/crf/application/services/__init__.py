from importlib import import_module

__all__ = [
    "CrfFieldTemplateImportService",
    "CrfTemplateApplicationService",
    "CrfFieldLookupQueryService",
    "CrfTemplateCommandService",
    "CrfTemplateQueryService",
]

_MODULE_BY_NAME = {
    "CrfFieldTemplateImportService": "apps.crf.application.services.field_template_import",
    "CrfTemplateApplicationService": "apps.crf.application.services.crf_template_application",
    "CrfFieldLookupQueryService": "apps.crf.application.services.field_lookup",
    "CrfTemplateCommandService": "apps.crf.application.services.crf_template_command",
    "CrfTemplateQueryService": "apps.crf.application.services.crf_template_query",
}


def __getattr__(name):
    module_name = _MODULE_BY_NAME.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
