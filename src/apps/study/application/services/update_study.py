from apps.study.application.commands.exceptions import StudyCodeAlreadyExistsError, StudyDateRangeError
from apps.study.application.commands.update_study import UpdateStudyCommand
from apps.study.application.queries.study_directory import StudyNotFoundError
from apps.study.infrastructure.repositories import DjangoStudyCommandRepository


class UpdateStudyService:
    repository_class = DjangoStudyCommandRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def execute(self, command: UpdateStudyCommand):
        study = self.repository.get_study(study_id=command.study_id)
        if study is None:
            raise StudyNotFoundError(command.study_id)

        self._validate_code_unique(command.code, exclude_id=command.study_id)
        self._validate_date_range(command.start_date, command.end_date)

        study.code = command.code.strip()
        study.name = command.name.strip()
        study.sponsor = command.sponsor.strip()
        study.description = command.description.strip()
        study.start_date = command.start_date
        study.end_date = command.end_date
        study.is_active = command.is_active
        self.repository.touch_study(study, actor_user_id=command.actor_user_id)

        return self.repository.save_study(study)

    def _validate_code_unique(self, code, exclude_id):
        if self.repository.study_code_exists(code=code, exclude_id=exclude_id):
            raise StudyCodeAlreadyExistsError(code)

    @staticmethod
    def _validate_date_range(start_date, end_date):
        if start_date and end_date and end_date < start_date:
            raise StudyDateRangeError(start_date, end_date)


__all__ = ["UpdateStudyService"]
