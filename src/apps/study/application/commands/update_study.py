from dataclasses import dataclass
from datetime import date

from apps.study.application.commands.exceptions import StudyCodeAlreadyExistsError, StudyDateRangeError
from apps.study.application.queries.study_directory import StudyNotFoundError
from apps.study.infrastructure.persistence.models import Study


@dataclass(frozen=True)
class UpdateStudyCommand:
    study_id: int
    code: str
    name: str
    sponsor: str
    description: str
    is_active: bool
    actor_user_id: int
    start_date: date | None = None
    end_date: date | None = None


class UpdateStudyService:
    def execute(self, command: UpdateStudyCommand) -> Study:
        study = Study.objects.filter(pk=command.study_id, deleted=False).first()
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
        study.updated_at = self._now()
        study.updated_by_id = command.actor_user_id
        study.save()

        return study

    @staticmethod
    def _validate_code_unique(code, exclude_id):
        if Study.objects.filter(code=code.strip(), deleted=False).exclude(pk=exclude_id).exists():
            raise StudyCodeAlreadyExistsError(code)

    @staticmethod
    def _validate_date_range(start_date, end_date):
        if start_date and end_date and end_date < start_date:
            raise StudyDateRangeError(start_date, end_date)

    @staticmethod
    def _now():
        from django.utils import timezone
        return timezone.now()
