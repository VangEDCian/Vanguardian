from django.db import transaction

from apps.study.application.commands.site_data import SiteCodeAlreadyExistsError
from apps.study.infrastructure.persistence.models import SiteMembership
from apps.study.models import Site
from django.utils import timezone

from .site_data import (
    CreateSiteCommand, DeleteSiteCommand, CreateSiteMembershipCommand,
    UpdateSiteCommand, DeleteSiteMembershipCommand, SiteMembershipNotFoundError, SiteNotFoundError,
    SiteMembershipAlreadyExistsError,
)


class CreateSiteService:
    @transaction.atomic
    def execute(self, command: CreateSiteCommand) -> Site:
        self._validate_code_unique(command.study_id, command.code)

        now = timezone.now()
        return Site.objects.create(
            code=command.code.strip(),
            name=command.name.strip(),
            investigator=command.investigator.strip(),
            study_id=command.study_id,
            is_active=command.is_active,
            created_at=now,
            updated_at=now,
            created_by_id=command.actor_user_id,
            updated_by_id=command.actor_user_id,
        )

    @staticmethod
    def _validate_code_unique(study_id, code):
        if Site.objects.filter(study_id=study_id, code=code.strip(), deleted=False).exists():
            raise SiteCodeAlreadyExistsError(code)


class DeleteSiteService:
    @transaction.atomic
    def execute(self, command: DeleteSiteCommand) -> Site:
        site = Site.objects.filter(pk=command.site_id, deleted=False).first()
        if site is None:
            raise SiteNotFoundError(command.site_id)

        site.deleted = True
        site.is_active = False
        site.updated_at = timezone.now()
        site.updated_by_id = command.actor_user_id
        site.save()
        return site


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
                f"User {command.user_id} is already a member of site {command.site_id}.",
            )

        now = timezone.now()
        return SiteMembership.objects.create(
            site_id=command.site_id,
            study_id=command.study_id,
            user_id=command.user_id,
            created_at=now,
            updated_at=now,
            created_by_id=command.actor_user_id,
            updated_by_id=command.actor_user_id,
        )


class DeleteSiteMembershipService:
    @transaction.atomic
    def execute(self, command: DeleteSiteMembershipCommand) -> SiteMembership:
        membership = SiteMembership.objects.filter(pk=command.membership_id, deleted=False).first()
        if membership is None:
            raise SiteMembershipNotFoundError(command.membership_id)

        membership.deleted = True
        membership.updated_at = timezone.now()
        membership.updated_by_id = command.actor_user_id
        membership.save()
        return membership


class UpdateSiteService:
    @transaction.atomic
    def execute(self, command: UpdateSiteCommand) -> Site:
        site = Site.objects.filter(pk=command.site_id, deleted=False).first()
        if site is None:
            raise SiteNotFoundError(command.site_id)
        site.name = command.name.strip()
        site.investigator = command.investigator.strip()
        site.is_active = command.is_active
        site.updated_at = timezone.now()
        site.updated_by_id = command.actor_user_id
        site.save()
        return site
