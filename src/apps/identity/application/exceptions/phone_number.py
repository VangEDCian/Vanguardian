from apps.shared.application import ApplicationValidationError


class PhoneNumberValidationError(ApplicationValidationError):
    default_message = "Invalid phone number."


__all__ = ["PhoneNumberValidationError"]
