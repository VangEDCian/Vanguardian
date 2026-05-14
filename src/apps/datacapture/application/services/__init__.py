from importlib import import_module

__all__ = [
    "DataCaptureFieldValidationRulesService",
    "DataCaptureEventTransitionTriggerResult",
    "DataCapturePageStateEventTransitionService",
    "DataCaptureSaveSubmitPageService",
    "DeleteDraftPageResult",
    "SavePageResult",
    "SubmitPageResult",
]

_MODULE_BY_NAME = {
    "DataCaptureFieldValidationRulesService": (
        "apps.datacapture.application.services.check_field_validation_rules"
    ),
    "DataCaptureEventTransitionTriggerResult": (
        "apps.datacapture.application.services.trigger_event_transition"
    ),
    "DataCapturePageStateEventTransitionService": (
        "apps.datacapture.application.services.trigger_event_transition"
    ),
    "DataCaptureSaveSubmitPageService": (
        "apps.datacapture.application.services.save_submit_page"
    ),
    "DeleteDraftPageResult": "apps.datacapture.application.services.save_submit_page",
    "SavePageResult": "apps.datacapture.application.services.save_submit_page",
    "SubmitPageResult": "apps.datacapture.application.services.save_submit_page",
}


def __getattr__(name):
    module_name = _MODULE_BY_NAME.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
