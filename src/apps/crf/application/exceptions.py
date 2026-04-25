class CrfTemplateNotFoundError(Exception):
    """Raised when a CRF template cannot be found for the requested selector."""


class CrfTemplateAmbiguousError(Exception):
    """Raised when a CRF template selector matches more than one template."""
