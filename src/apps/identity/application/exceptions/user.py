from apps.shared.application import ApplicationNotFoundError, ApplicationValidationError


class IdentityUsernameAlreadyExistsError(ApplicationValidationError):
    default_message = "Username already exists."


class IdentityUserEmailAlreadyExistsError(ApplicationValidationError):
    default_message = "Email already exists."


class IdentityUserPhoneNumberAlreadyExistsError(ApplicationValidationError):
    default_message = "Phone number already exists."


class IdentityUserRestoreDataNotFoundError(ApplicationNotFoundError):
    default_message = "Identity user restore data was not found."


class IdentityUserNotFoundError(ApplicationNotFoundError):
    default_message = "Identity user was not found."


__all__ = [
    "IdentityUserEmailAlreadyExistsError",
    "IdentityUserNotFoundError",
    "IdentityUserPhoneNumberAlreadyExistsError",
    "IdentityUserRestoreDataNotFoundError",
    "IdentityUsernameAlreadyExistsError",
]
