from dataclasses import dataclass

from django.db import transaction

from apps.shared.application.services.soft_delete import build_soft_deleted_unique_value
from apps.study.application.queries.study_directory import StudyNotFoundError
from apps.study.infrastructure.persistence.models import Study


@dataclass(frozen=True)
class DeleteStudyCommand:
    study_id: int
    actor_user_id: int


class DeleteStudyService:
    @transaction.atomic
    def execute(self, command: DeleteStudyCommand) -> Study:
        study = Study.objects.filter(pk=command.study_id, deleted=False).first()
        if study is None:
            raise StudyNotFoundError(command.study_id)

        study.code = build_soft_deleted_unique_value(study.code)
        study.deleted = True
        study.is_active = False
        study.updated_at = self._now()
        study.updated_by_id = command.actor_user_id
        study.save()
        return study

    @staticmethod
    def _now():
        from django.utils import timezone

        return timezone.now()
