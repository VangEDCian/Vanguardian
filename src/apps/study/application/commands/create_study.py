from dataclasses import dataclass
from datetime import date

from apps.study.application.commands.exceptions import StudyCodeAlreadyExistsError, StudyDateRangeError
from apps.study.infrastructure.persistence.models import Study


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
    def execute(self, command: CreateStudyCommand) -> Study:
        self._validate_code_unique(command.code)
        self._validate_date_range(command.start_date, command.end_date)

        now = self._now()
        return Study.objects.create(
            code=command.code.strip(),
            name=command.name.strip(),
            sponsor=command.sponsor.strip(),
            description=command.description.strip(),
            start_date=command.start_date,
            end_date=command.end_date,
            is_active=command.is_active,
            created_at=now,
            updated_at=now,
            created_by_id=command.actor_user_id,
            updated_by_id=command.actor_user_id,
        )

    @staticmethod
    def _validate_code_unique(code):
        if Study.objects.filter(code=code.strip(), deleted=False).exists():
            raise StudyCodeAlreadyExistsError(code)

    @staticmethod
    def _validate_date_range(start_date, end_date):
        if start_date and end_date and end_date < start_date:
            raise StudyDateRangeError(start_date, end_date)

    @staticmethod
    def _now():
        from django.utils import timezone
        return timezone.now()
