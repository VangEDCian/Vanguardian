from importlib import import_module

__all__ = ["CreateSubjectService"]

_MODULE_BY_NAME = {
    "CreateSubjectService": "apps.subject.application.services.create_subject",
}


def __getattr__(name):
    module_name = _MODULE_BY_NAME.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
