from django.db import transaction

from apps.shared.application.services.soft_delete import build_soft_deleted_unique_value
from apps.study.application.commands.site_data import SiteCodeAlreadyExistsError
from apps.study.infrastructure.repositories import DjangoStudyCommandRepository

from apps.study.application.commands.site_data import (
    CreateSiteCommand,
    CreateSiteMembershipCommand,
    DeleteSiteCommand,
    DeleteSiteMembershipCommand,
    SiteMembershipAlreadyExistsError,
    SiteMembershipNotFoundError,
    SiteNotFoundError,
    UpdateSiteCommand,
)


class CreateSiteService:
    repository_class = DjangoStudyCommandRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    @transaction.atomic
    def execute(self, command: CreateSiteCommand):
        self._validate_code_unique(command.study_id, command.code)

        return self.repository.create_site(
            code=command.code.strip(),
            name=command.name.strip(),
            investigator=command.investigator.strip(),
            study_id=command.study_id,
            is_active=command.is_active,
            actor_user_id=command.actor_user_id,
        )

    def _validate_code_unique(self, study_id, code):
        if self.repository.site_code_exists(study_id=study_id, code=code):
            raise SiteCodeAlreadyExistsError(code)


class DeleteSiteService:
    repository_class = DjangoStudyCommandRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    @transaction.atomic
    def execute(self, command: DeleteSiteCommand):
        site = self.repository.get_site(site_id=command.site_id)
        if site is None:
            raise SiteNotFoundError(command.site_id)

        site.code = build_soft_deleted_unique_value(site.code)
        site.deleted = True
        site.is_active = False
        self.repository.touch_site(site, actor_user_id=command.actor_user_id)
        return self.repository.save_site(site)


class CreateSiteMembershipService:
    repository_class = DjangoStudyCommandRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    @transaction.atomic
    def execute(self, command: CreateSiteMembershipCommand):
        if not self.repository.site_exists(site_id=command.site_id):
            raise SiteNotFoundError(command.site_id)

        if self.repository.site_membership_exists(site_id=command.site_id, user_id=command.user_id):
            raise SiteMembershipAlreadyExistsError(
                f"User {command.user_id} is already a member of site {command.site_id}.",
            )

        return self.repository.create_site_membership(
            site_id=command.site_id,
            study_id=command.study_id,
            user_id=command.user_id,
            actor_user_id=command.actor_user_id,
        )


class DeleteSiteMembershipService:
    repository_class = DjangoStudyCommandRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    @transaction.atomic
    def execute(self, command: DeleteSiteMembershipCommand):
        membership = self.repository.get_site_membership(membership_id=command.membership_id)
        if membership is None:
            raise SiteMembershipNotFoundError(command.membership_id)

        membership.deleted = True
        self.repository.touch_site_membership(membership, actor_user_id=command.actor_user_id)
        return self.repository.save_site_membership(membership)


class UpdateSiteService:
    repository_class = DjangoStudyCommandRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    @transaction.atomic
    def execute(self, command: UpdateSiteCommand):
        site = self.repository.get_site(site_id=command.site_id)
        if site is None:
            raise SiteNotFoundError(command.site_id)
        site.name = command.name.strip()
        site.investigator = command.investigator.strip()
        site.is_active = command.is_active
        self.repository.touch_site(site, actor_user_id=command.actor_user_id)
        return self.repository.save_site(site)


__all__ = [
    "CreateSiteMembershipService",
    "CreateSiteService",
    "DeleteSiteMembershipService",
    "DeleteSiteService",
    "UpdateSiteService",
]
