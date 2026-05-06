from django.db import transaction

from apps.shared.application.services.soft_delete import build_soft_deleted_unique_value
from apps.study.application.commands.delete_study import DeleteStudyCommand
from apps.study.application.queries.study_directory import StudyNotFoundError
from apps.study.infrastructure.repositories import DjangoStudyCommandRepository
from apps.study.infrastructure.sonic import SonicStudySiteAdapter


class DeleteStudyService:
    repository_class = DjangoStudyCommandRepository
    sonic_adapter_class = SonicStudySiteAdapter

    def __init__(self, repository=None, sonic_adapter=None):
        self.repository = repository or self.repository_class()
        self.sonic_adapter = sonic_adapter or self.sonic_adapter_class()

    @transaction.atomic
    def execute(self, command: DeleteStudyCommand):
        study = self.repository.get_study(study_id=command.study_id)
        if study is None:
            raise StudyNotFoundError(command.study_id)

        study.code = build_soft_deleted_unique_value(study.code)
        study.deleted = True
        study.is_active = False
        self.repository.touch_study(study, actor_user_id=command.actor_user_id)
        deleted_study = self.repository.save_study(study)
        self.sonic_adapter.remove_study(study_id=deleted_study.pk)
        return deleted_study


__all__ = ["DeleteStudyService"]
