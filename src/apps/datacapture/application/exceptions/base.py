from apps.shared.application import ApplicationValidationError


class DataCaptureUseCaseError(ApplicationValidationError):
    """Base exception for datacapture application use cases."""

    default_message = "Datacapture use case failed."


class DataCaptureValidationError(DataCaptureUseCaseError):
    """Base reusable validation exception for datacapture use cases."""

    default_message = "Datacapture validation failed."


__all__ = ["DataCaptureUseCaseError", "DataCaptureValidationError"]
