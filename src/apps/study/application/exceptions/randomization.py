from apps.shared.application import ApplicationNotFoundError, ApplicationValidationError


class RandomizationDeleteBlockedError(ApplicationValidationError):
    default_message = "Randomization delete is blocked."


class RandomizationSchemeNotFoundError(ApplicationNotFoundError):
    default_message = "Randomization scheme was not found."


class RandomizationArmNotFoundError(ApplicationNotFoundError):
    default_message = "Randomization arm was not found."


class RandomizationSlotGenerationError(ApplicationValidationError):
    """Raised when randomization slot generation cannot be safely performed."""

    default_message = "Randomization slot generation failed."


__all__ = [
    "RandomizationArmNotFoundError",
    "RandomizationDeleteBlockedError",
    "RandomizationSchemeNotFoundError",
    "RandomizationSlotGenerationError",
]
