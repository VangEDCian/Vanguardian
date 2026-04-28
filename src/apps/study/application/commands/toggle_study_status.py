from dataclasses import dataclass

from apps.study.application.queries.study_directory import StudyNotFoundError
from apps.study.infrastructure.repositories import DjangoStudyCommandRepository


@dataclass(frozen=True)
class ToggleStudyStatusCommand:
    study_id: int
    actor_user_id: int


class ToggleStudyStatusService:
    repository_class = DjangoStudyCommandRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def execute(self, command: ToggleStudyStatusCommand):
        study = self.repository.get_study(study_id=command.study_id)
        if study is None:
            raise StudyNotFoundError(command.study_id)

        study.is_active = not study.is_active
        self.repository.touch_study(study, actor_user_id=command.actor_user_id)

        return self.repository.save_study(study)
