from dataclasses import dataclass


class DataCapturePageStateNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class TriggerPageStateEventTransitionCommand:
    page_state_id: int
    actor_user_id: int | None = None
    trigger_source: str = "datacapture"


__all__ = [
    "DataCapturePageStateNotFoundError",
    "TriggerPageStateEventTransitionCommand",
]
