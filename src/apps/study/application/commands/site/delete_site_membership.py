from dataclasses import dataclass

from django.db import transaction

from apps.study.models import SiteMembership
from .membership_exceptions import SiteMembershipNotFoundError


@dataclass(frozen=True)
class DeleteSiteMembershipCommand:
    membership_id: int
    actor_user_id: int


class DeleteSiteMembershipService:
    @transaction.atomic
    def execute(self, command: DeleteSiteMembershipCommand) -> SiteMembership:
        membership = SiteMembership.objects.filter(pk=command.membership_id, deleted=False).first()
        if membership is None:
            raise SiteMembershipNotFoundError(command.membership_id)

        membership.deleted = True
        membership.updated_at = self._now()
        membership.updated_by_id = command.actor_user_id
        membership.save()
        return membership

    @staticmethod
    def _now():
        from django.utils import timezone
        return timezone.now()

