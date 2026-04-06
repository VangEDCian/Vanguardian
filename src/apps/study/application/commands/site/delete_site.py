from dataclasses import dataclass

from django.db import transaction

from apps.study.application.queries.site.exceptions import SiteNotFoundError
from apps.study.models import Site


@dataclass(frozen=True)
class DeleteSiteCommand:
    site_id: int
    actor_user_id: int


class DeleteSiteService:
    @transaction.atomic
    def execute(self, command: DeleteSiteCommand) -> Site:
        site = Site.objects.filter(pk=command.site_id, deleted=False).first()
        if site is None:
            raise SiteNotFoundError(command.site_id)

        site.deleted = True
        site.is_active = False
        site.updated_at = self._now()
        site.updated_by_id = command.actor_user_id
        site.save()
        return site

    @staticmethod
    def _now():
        from django.utils import timezone

        return timezone.now()
