from apps.shared.application import ApplicationNotFoundError


class DataCapturePageStateNotFoundError(ApplicationNotFoundError):
    default_message = "Data capture page state was not found."


__all__ = ["DataCapturePageStateNotFoundError"]
