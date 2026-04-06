from dataclasses import dataclass

from django.db import transaction

from .membership_exceptions import (
    SiteMembershipAlreadyExistsError,
)
from apps.study.models import Site, SiteMembership
from apps.study.application.queries.site.exceptions import SiteNotFoundError


@dataclass(frozen=True)
class CreateSiteMembershipCommand:
    site_id: int
    study_id: int
    user_id: int
    actor_user_id: int


class CreateSiteMembershipService:
    @transaction.atomic
    def execute(self, command: CreateSiteMembershipCommand) -> SiteMembership:
        if not Site.objects.filter(pk=command.site_id, deleted=False).exists():
            raise SiteNotFoundError(command.site_id)

        if SiteMembership.objects.filter(
            site_id=command.site_id,
            user_id=command.user_id,
            deleted=False,
        ).exists():
            raise SiteMembershipAlreadyExistsError(
                f"User {command.user_id} is already a member of site {command.site_id}."
            )

        now = self._now()
        return SiteMembership.objects.create(
            site_id=command.site_id,
            study_id=command.study_id,
            user_id=command.user_id,
            created_at=now,
            updated_at=now,
            created_by_id=command.actor_user_id,
            updated_by_id=command.actor_user_id,
        )

    @staticmethod
    def _now():
        from django.utils import timezone
        return timezone.now()

