from importlib import import_module

__all__ = [
    "DataCaptureFieldValidationRulesService",
    "DataCaptureEventTransitionTriggerResult",
    "DataCaptureEventFactEvaluation",
    "DataCaptureEventAttestationService",
    "DataCaptureFactEvaluation",
    "DataCaptureFactEvaluationService",
    "DataCaptureFactMappingConfigService",
    "DataCaptureFactMappingUpsertResult",
    "DataCaptureFactSnapshot",
    "DataCaptureFactSnapshotService",
    "DataCapturePageStateEventTransitionService",
    "DataCaptureSaveSubmitPageService",
    "DeleteDraftPageResult",
    "PageEntryStateChangeEventDispatcher",
    "PageEntrySubmittedEventContext",
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
    "DataCaptureEventFactEvaluation": "apps.datacapture.application.services.fact_evaluation",
    "DataCaptureEventAttestationService": "apps.datacapture.application.services.event_attestation",
    "DataCaptureFactEvaluation": "apps.datacapture.application.services.fact_evaluation",
    "DataCaptureFactEvaluationService": "apps.datacapture.application.services.fact_evaluation",
    "DataCaptureFactMappingConfigService": "apps.datacapture.application.services.fact_mapping_config",
    "DataCaptureFactMappingUpsertResult": "apps.datacapture.application.services.fact_mapping_config",
    "DataCaptureFactSnapshot": "apps.datacapture.application.services.fact_snapshot",
    "DataCaptureFactSnapshotService": "apps.datacapture.application.services.fact_snapshot",
    "DataCapturePageStateEventTransitionService": (
        "apps.datacapture.application.services.trigger_event_transition"
    ),
    "DataCaptureSaveSubmitPageService": (
        "apps.datacapture.application.services.save_submit_page"
    ),
    "DeleteDraftPageResult": "apps.datacapture.application.services.save_submit_page",
    "PageEntryStateChangeEventDispatcher": (
        "apps.datacapture.application.services.pageentry_state_change_events"
    ),
    "PageEntrySubmittedEventContext": (
        "apps.datacapture.application.services.pageentry_state_change_events"
    ),
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
