from apps.shared.application import ApplicationValidationError


class SubjectUseCaseError(ApplicationValidationError):
    """Base exception for subject application use cases."""

    default_message = "Subject use case failed."


class SubjectValidationError(SubjectUseCaseError):
    """Base reusable validation exception for subject use cases."""

    default_message = "Subject validation failed."


__all__ = ["SubjectUseCaseError", "SubjectValidationError"]
