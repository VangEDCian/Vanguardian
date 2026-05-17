from apps.datacapture.application.exceptions.base import DataCaptureValidationError


class DataCaptureChangeReasonRequiredError(DataCaptureValidationError):
    default_message = "Change reason is required for all updated fields before submit."


class DataCaptureNoActiveDraftError(DataCaptureValidationError):
    default_message = "No active draft version to delete."


class DataCaptureInvalidPayloadUseCaseError(DataCaptureValidationError):
    default_message = "Invalid or empty payload."


class DataCaptureUnsupportedEntryStatusUseCaseError(DataCaptureValidationError):
    default_message = "Unsupported page entry status."


__all__ = [
    "DataCaptureChangeReasonRequiredError",
    "DataCaptureInvalidPayloadUseCaseError",
    "DataCaptureNoActiveDraftError",
    "DataCaptureUnsupportedEntryStatusUseCaseError",
]
