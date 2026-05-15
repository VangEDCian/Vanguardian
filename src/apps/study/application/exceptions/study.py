from apps.shared.application import ApplicationNotFoundError, ApplicationValidationError


class StudyNotFoundError(ApplicationNotFoundError):
    default_message = "Study was not found."


class StudyCodeAlreadyExistsError(ApplicationValidationError):
    default_message = "Study code already exists."


class StudyDateRangeError(ApplicationValidationError):
    default_message = "Study date range is invalid."


__all__ = [
    "StudyCodeAlreadyExistsError",
    "StudyDateRangeError",
    "StudyNotFoundError",
]
