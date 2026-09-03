from apps.shared.application import ApplicationNotFoundError, ApplicationValidationError


class StudyNotFoundError(ApplicationNotFoundError):
    default_message = "Study was not found."


class StudyCodeAlreadyExistsError(ApplicationValidationError):
    default_message = "Study code already exists."


class StudyDateRangeError(ApplicationValidationError):
    default_message = "Study date range is invalid."


class StudySubjectIdentifierMigrationError(ApplicationValidationError):
    default_message = "Subject identifier migration could not be completed."

    def __init__(self, preview, message=None):
        self.preview = preview
        super().__init__(message)


class StudySubjectIdentifierMigrationRequiredError(
    StudySubjectIdentifierMigrationError
):
    default_message = "Subject identifier migration confirmation is required."


class StudySubjectIdentifierMigrationBlockedError(
    StudySubjectIdentifierMigrationError
):
    default_message = "Subject identifier migration is blocked by preflight issues."


class StudySubjectIdentifierMigrationStalePlanError(
    StudySubjectIdentifierMigrationError
):
    default_message = "Subject identifier migration preview is stale."


__all__ = [
    "StudyCodeAlreadyExistsError",
    "StudyDateRangeError",
    "StudyNotFoundError",
    "StudySubjectIdentifierMigrationBlockedError",
    "StudySubjectIdentifierMigrationError",
    "StudySubjectIdentifierMigrationRequiredError",
    "StudySubjectIdentifierMigrationStalePlanError",
]
