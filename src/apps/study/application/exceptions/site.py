from apps.shared.application import ApplicationNotFoundError, ApplicationValidationError


class SiteCodeAlreadyExistsError(ApplicationValidationError):
    default_message = "Site code already exists."


class SiteMembershipAlreadyExistsError(ApplicationValidationError):
    default_message = "Site membership already exists."


class SiteMembershipNotFoundError(ApplicationNotFoundError):
    default_message = "Site membership was not found."


class SiteNotFoundError(ApplicationNotFoundError):
    default_message = "Site was not found."


__all__ = [
    "SiteCodeAlreadyExistsError",
    "SiteMembershipAlreadyExistsError",
    "SiteMembershipNotFoundError",
    "SiteNotFoundError",
]
