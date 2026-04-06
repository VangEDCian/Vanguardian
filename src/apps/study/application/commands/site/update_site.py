from dataclasses import dataclass

from django.db import transaction

from apps.study.application.queries.site.exceptions import SiteNotFoundError
from apps.study.models import Site

from .exceptions import SiteCodeAlreadyExistsError


@dataclass(frozen=True)
class UpdateSiteCommand:
    site_id: int
    code: str
    name: str
    investigator: str
    study_id: int
    is_active: bool
    actor_user_id: int


class UpdateSiteService:
    @transaction.atomic
    def execute(self, command: UpdateSiteCommand) -> Site:
        site = Site.objects.filter(pk=command.site_id, deleted=False).first()
        if site is None:
            raise SiteNotFoundError(command.site_id)

        self._validate_code_unique(command.study_id, command.code, exclude_id=command.site_id)

        site.code = command.code.strip()
        site.name = command.name.strip()
        site.investigator = command.investigator.strip()
        site.study_id = command.study_id
        site.is_active = command.is_active
        site.updated_at = self._now()
        site.updated_by_id = command.actor_user_id
        site.save()
        return site

    @staticmethod
    def _validate_code_unique(study_id, code, exclude_id):
        if (
                Site.objects.filter(study_id=study_id, code=code.strip(), deleted=False)
                        .exclude(pk=exclude_id)
                        .exists()
        ):
            raise SiteCodeAlreadyExistsError(code)

    @staticmethod
    def _now():
        from django.utils import timezone

        return timezone.now()
