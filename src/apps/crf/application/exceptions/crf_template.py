from apps.shared.application import ApplicationAmbiguousError, ApplicationNotFoundError


class CrfTemplateNotFoundError(ApplicationNotFoundError):
    """Raised when a CRF template cannot be found for the requested selector."""


class CrfTemplateAmbiguousError(ApplicationAmbiguousError):
    """Raised when a CRF template selector matches more than one template."""


__all__ = ["CrfTemplateAmbiguousError", "CrfTemplateNotFoundError"]
