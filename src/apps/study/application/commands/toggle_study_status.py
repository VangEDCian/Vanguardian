from dataclasses import dataclass

from apps.study.application.queries.study_directory import StudyNotFoundError
from apps.study.infrastructure.persistence.models import Study


@dataclass(frozen=True)
class ToggleStudyStatusCommand:
    study_id: int
    actor_user_id: int


class ToggleStudyStatusService:
    def execute(self, command: ToggleStudyStatusCommand) -> Study:
        study = Study.objects.filter(pk=command.study_id, deleted=False).first()
        if study is None:
            raise StudyNotFoundError(command.study_id)

        study.is_active = not study.is_active
        study.updated_at = self._now()
        study.updated_by_id = command.actor_user_id
        study.save()

        return study

    @staticmethod
    def _now():
        from django.utils import timezone
        return timezone.now()
