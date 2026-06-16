class PageCaptureDomainError(Exception):
    """Base for page capture (save draft / submit) domain rules."""


class PageNotEditableError(PageCaptureDomainError):
    """Raised when ``PageState`` is in a stable / non-editable workflow status."""


class InvalidPagePayloadError(PageCaptureDomainError):
    """Raised when the JSON payload is missing or not a usable object."""


class UnsupportedEntryStatusError(PageCaptureDomainError):
    """Raised when the latest ``PageEntry`` status cannot be handled for the requested operation."""
