from dataclasses import dataclass
from datetime import date

from apps.study.application.commands.exceptions import StudyCodeAlreadyExistsError, StudyDateRangeError
from apps.study.infrastructure.repositories import DjangoStudyCommandRepository


@dataclass(frozen=True)
class CreateStudyCommand:
    code: str
    name: str
    sponsor: str
    description: str
    is_active: bool
    actor_user_id: int
    start_date: date | None = None
    end_date: date | None = None


class CreateStudyService:
    repository_class = DjangoStudyCommandRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def execute(self, command: CreateStudyCommand):
        self._validate_code_unique(command.code)
        self._validate_date_range(command.start_date, command.end_date)

        return self.repository.create_study(
            code=command.code.strip(),
            name=command.name.strip(),
            sponsor=command.sponsor.strip(),
            description=command.description.strip(),
            start_date=command.start_date,
            end_date=command.end_date,
            is_active=command.is_active,
            actor_user_id=command.actor_user_id,
        )

    def _validate_code_unique(self, code):
        if self.repository.study_code_exists(code=code):
            raise StudyCodeAlreadyExistsError(code)

    @staticmethod
    def _validate_date_range(start_date, end_date):
        if start_date and end_date and end_date < start_date:
            raise StudyDateRangeError(start_date, end_date)
