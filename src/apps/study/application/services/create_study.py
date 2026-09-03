from apps.study.application.commands.create_study import CreateStudyCommand
from apps.study.application.commands.exceptions import StudyCodeAlreadyExistsError, StudyDateRangeError
from apps.study.domain import StudySubjectIdentifierPolicy
from apps.study.infrastructure.repositories import DjangoStudyCommandRepository
from apps.study.infrastructure.sonic import SonicStudySiteAdapter


class CreateStudyService:
    repository_class = DjangoStudyCommandRepository
    sonic_adapter_class = SonicStudySiteAdapter

    def __init__(self, repository=None, sonic_adapter=None):
        self.repository = repository or self.repository_class()
        self.sonic_adapter = sonic_adapter or self.sonic_adapter_class()

    def execute(self, command: CreateStudyCommand):
        self._validate_code_unique(command.code)
        self._validate_date_range(command.start_date, command.end_date)
        self._build_identifier_policy(command).validate()

        study = self.repository.create_study(
            code=command.code.strip(),
            name=command.name.strip(),
            sponsor=command.sponsor.strip(),
            description=command.description.strip(),
            start_date=command.start_date,
            end_date=command.end_date,
            is_active=command.is_active,
            actor_user_id=command.actor_user_id,
            subject_identifier_mode=command.subject_identifier_mode,
            screening_identifier_mode=command.screening_identifier_mode,
            subject_code_pattern=command.subject_code_pattern,
            screening_code_pattern=command.screening_code_pattern,
            subject_code_uniqueness_scope=command.subject_code_uniqueness_scope,
            lock_subject_code_after_assignment=command.lock_subject_code_after_assignment,
        )
        self.sonic_adapter.index_study(
            study_id=study.pk,
            code=study.code,
            name=command.name.strip(),
            sponsor=command.sponsor.strip(),
            description=command.description.strip(),
        )
        return study

    def _validate_code_unique(self, code):
        if self.repository.study_code_exists(code=code):
            raise StudyCodeAlreadyExistsError(code)

    @staticmethod
    def _build_identifier_policy(command: CreateStudyCommand):
        return StudySubjectIdentifierPolicy(
            study_id=0,
            study_code=command.code,
            subject_identifier_mode=command.subject_identifier_mode,
            screening_identifier_mode=command.screening_identifier_mode,
            subject_code_pattern=command.subject_code_pattern,
            screening_code_pattern=command.screening_code_pattern,
            subject_code_uniqueness_scope=command.subject_code_uniqueness_scope,
            lock_subject_code_after_assignment=command.lock_subject_code_after_assignment,
        )

    @staticmethod
    def _validate_date_range(start_date, end_date):
        if start_date and end_date and end_date < start_date:
            raise StudyDateRangeError(start_date, end_date)


__all__ = ["CreateStudyService"]
