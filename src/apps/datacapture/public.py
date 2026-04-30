from apps.datacapture.application import (
    DataCapturePageStateEventTransitionService,
    DataCapturePageStateNotFoundError,
    TriggerPageStateEventTransitionCommand,
)


class DataCaptureEventTransitionAdapter:
    def __init__(self, page_state_event_transition_service=None):
        self.page_state_event_transition_service = (
            page_state_event_transition_service or DataCapturePageStateEventTransitionService()
        )

    def trigger_for_page_state(
        self,
        *,
        page_state_id: int,
        actor_user_id: int | None = None,
        trigger_source: str = "datacapture",
    ):
        command = TriggerPageStateEventTransitionCommand(
            page_state_id=page_state_id,
            actor_user_id=actor_user_id,
            trigger_source=trigger_source,
        )
        return self.page_state_event_transition_service.execute(command)


def trigger_event_transition_for_page_state(
    *,
    page_state_id: int,
    actor_user_id: int | None = None,
    trigger_source: str = "datacapture",
):
    return DataCaptureEventTransitionAdapter().trigger_for_page_state(
        page_state_id=page_state_id,
        actor_user_id=actor_user_id,
        trigger_source=trigger_source,
    )


__all__ = [
    "DataCaptureEventTransitionAdapter",
    "DataCapturePageStateNotFoundError",
    "trigger_event_transition_for_page_state",
]
