from dataclasses import dataclass

from django.db import transaction

from apps.identity.application.queries import IdentityUserNotFoundError
from apps.identity.models import User

DELETED_USERNAME_PREFIX = "deleted-user-"


@dataclass(frozen=True)
class DeleteIdentityUserCommand:
    user_id: int
    actor_user_id: int


class DeleteIdentityUserService:
    @transaction.atomic
    def execute(self, command: DeleteIdentityUserCommand) -> None:
        user = User.objects.filter(pk=command.user_id).first()
        if user is None:
            raise IdentityUserNotFoundError(command.user_id)

        user.username = f"{DELETED_USERNAME_PREFIX}{user.pk}"
        user.first_name = ""
        user.last_name = ""
        user.display_name = "Deleted User"
        user.email = None
        user.phone_number = None
        user.is_active = False
        user.is_staff = False
        user.is_superuser = False
        user.save()
        user.groups.clear()
