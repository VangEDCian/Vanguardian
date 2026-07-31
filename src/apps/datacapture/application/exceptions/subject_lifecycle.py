from apps.datacapture.application.exceptions.base import DataCaptureValidationError


class DataCaptureSubjectLifecycleError(DataCaptureValidationError):
    default_message = (
        "Data capture is not allowed because the subject lifecycle blocks this visit."
    )


__all__ = ["DataCaptureSubjectLifecycleError"]
