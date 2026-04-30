from importlib import import_module

__all__ = [
    "DataCaptureEventTransitionTriggerResult",
    "DataCapturePageStateEventTransitionService",
]

_MODULE_BY_NAME = {
    "DataCaptureEventTransitionTriggerResult": (
        "apps.datacapture.application.services.trigger_event_transition"
    ),
    "DataCapturePageStateEventTransitionService": (
        "apps.datacapture.application.services.trigger_event_transition"
    ),
}


def __getattr__(name):
    module_name = _MODULE_BY_NAME.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
