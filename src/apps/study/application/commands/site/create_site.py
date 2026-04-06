from dataclasses import dataclass

from django.db import transaction

from apps.study.application.commands.site.exceptions import SiteCodeAlreadyExistsError
from apps.study.models import Site


@dataclass(frozen=True)
class CreateSiteCommand:
    code: str
    name: str
    investigator: str
    study_id: int
    is_active: bool
    actor_user_id: int


class CreateSiteService:
    @transaction.atomic
    def execute(self, command: CreateSiteCommand) -> Site:
        self._validate_code_unique(command.study_id, command.code)

        now = self._now()
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

    @staticmethod
    def _now():
        from django.utils import timezone

        return timezone.now()

