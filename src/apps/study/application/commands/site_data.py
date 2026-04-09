from dataclasses import dataclass


@dataclass(frozen=True)
class CreateSiteCommand:
    code: str
    name: str
    investigator: str
    study_id: int
    is_active: bool
    actor_user_id: int


@dataclass(frozen=True)
class DeleteSiteCommand:
    site_id: int
    actor_user_id: int


class SiteCodeAlreadyExistsError(Exception):
    pass


@dataclass(frozen=True)
class CreateSiteMembershipCommand:
    site_id: int
    study_id: int
    user_id: int
    actor_user_id: int


@dataclass(frozen=True)
class DeleteSiteMembershipCommand:
    membership_id: int
    actor_user_id: int


class SiteMembershipAlreadyExistsError(Exception):
    pass


class SiteMembershipNotFoundError(Exception):
    pass


class SiteNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class UpdateSiteCommand:
    site_id: int
    name: str
    investigator: str
    is_active: bool
    actor_user_id: int
