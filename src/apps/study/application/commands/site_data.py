from dataclasses import dataclass

from apps.study.application.exceptions import (
    SiteCodeAlreadyExistsError as SiteCodeAlreadyExistsError,
)
from apps.study.application.exceptions import (
    SiteMembershipAlreadyExistsError as SiteMembershipAlreadyExistsError,
)
from apps.study.application.exceptions import (
    SiteMembershipNotFoundError as SiteMembershipNotFoundError,
)
from apps.study.application.exceptions import (
    SiteNotFoundError as SiteNotFoundError,
)


@dataclass(frozen=True)
class CreateSiteCommand:
    code: str
    name: str
    investigator_id: int | None
    study_id: int
    is_active: bool
    actor_user_id: int


@dataclass(frozen=True)
class DeleteSiteCommand:
    site_id: int
    actor_user_id: int


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


@dataclass(frozen=True)
class UpdateSiteCommand:
    site_id: int
    name: str
    investigator_id: int | None
    is_active: bool
    actor_user_id: int
