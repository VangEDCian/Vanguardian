from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist, ValidationError


class ApplicationValidationError(ValidationError):
    """Base validation exception for application-layer use cases."""

    default_message = "Application validation failed."

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)

    def __str__(self):
        return str(self.message)


class ApplicationNotFoundError(ObjectDoesNotExist):
    """Base not-found exception for application-layer use cases."""

    default_message = "Requested application resource was not found."

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)

    def __str__(self):
        return str(self.message)


class ApplicationAmbiguousError(MultipleObjectsReturned):
    """Base ambiguous-result exception for application-layer use cases."""

    default_message = "Application query returned multiple matching resources."

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)

    def __str__(self):
        return str(self.message)


__all__ = [
    "ApplicationAmbiguousError",
    "ApplicationNotFoundError",
    "ApplicationValidationError",
]
