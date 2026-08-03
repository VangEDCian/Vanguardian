from django.db import transaction

from apps.study.application.commands.exceptions import StudyCodeAlreadyExistsError, StudyDateRangeError
from apps.study.application.commands.update_study import UpdateStudyCommand
from apps.study.application.exceptions import (
    StudySubjectIdentifierMigrationBlockedError,
    StudySubjectIdentifierMigrationRequiredError,
    StudySubjectIdentifierMigrationStalePlanError,
)
from apps.study.application.queries.study_directory import StudyNotFoundError
from apps.study.domain import StudySubjectIdentifierPolicy
from apps.study.infrastructure.repositories import DjangoStudyCommandRepository


class UpdateStudyService:
    repository_class = DjangoStudyCommandRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def execute(self, command: UpdateStudyCommand):
        with transaction.atomic():
            study = self._get_study_for_update(study_id=command.study_id)
            if study is None:
                raise StudyNotFoundError(command.study_id)

            self._validate_code_unique(command.code, exclude_id=command.study_id)
            self._validate_date_range(command.start_date, command.end_date)
            current_policy = self._build_identifier_policy_from_study(study)
            target_policy = self._build_identifier_policy(command)
            target_policy.validate()

            if self._identifier_assignment_changed(
                study=study,
                command=command,
            ):
                self._migrate_subject_identifiers(
                    study=study,
                    current_policy=current_policy,
                    target_policy=target_policy,
                    command=command,
                )

            study.code = command.code.strip()
            study.name = command.name.strip()
            study.sponsor = command.sponsor.strip()
            study.description = command.description.strip()
            study.start_date = command.start_date
            study.end_date = command.end_date
            study.is_active = command.is_active
            study.subject_identifier_mode = command.subject_identifier_mode
            study.screening_identifier_mode = command.screening_identifier_mode
            study.subject_code_pattern = command.subject_code_pattern
            study.screening_code_pattern = command.screening_code_pattern
            study.subject_code_uniqueness_scope = command.subject_code_uniqueness_scope
            study.lock_subject_code_after_assignment = (
                command.lock_subject_code_after_assignment
            )
            self.repository.touch_study(study, actor_user_id=command.actor_user_id)

            return self.repository.save_study(study)

    def preview_identifier_policy_migration(self, command: UpdateStudyCommand):
        study = self.repository.get_study(study_id=command.study_id)
        if study is None:
            raise StudyNotFoundError(command.study_id)
        target_policy = self._build_identifier_policy(command)
        target_policy.validate()
        from apps.subject.public import preview_subject_identifier_policy_migration

        return preview_subject_identifier_policy_migration(
            study_id=command.study_id,
            current_policy=self._build_identifier_policy_from_study(study),
            target_policy=target_policy,
        )

    def _get_study_for_update(self, *, study_id):
        getter = getattr(self.repository, "get_study_for_update", None)
        if getter is not None:
            return getter(study_id=study_id)
        return self.repository.get_study(study_id=study_id)

    @staticmethod
    def _identifier_assignment_changed(*, study, command):
        if study.subject_identifier_mode != command.subject_identifier_mode:
            return True
        if study.subject_code_pattern != command.subject_code_pattern:
            return True
        if (
            study.subject_code_uniqueness_scope
            != command.subject_code_uniqueness_scope
        ):
            return True
        return False

    @staticmethod
    def _build_identifier_policy_from_study(study):
        return StudySubjectIdentifierPolicy(
            study_id=study.pk,
            study_code=study.code,
            subject_identifier_mode=study.subject_identifier_mode,
            screening_identifier_mode=study.screening_identifier_mode,
            subject_code_pattern=study.subject_code_pattern,
            screening_code_pattern=study.screening_code_pattern,
            subject_code_uniqueness_scope=study.subject_code_uniqueness_scope,
            lock_subject_code_after_assignment=study.lock_subject_code_after_assignment,
        )

    @staticmethod
    def _migrate_subject_identifiers(
        *, study, current_policy, target_policy, command
    ):
        from apps.subject.public import (
            SubjectIdentifierMigrationBlockedError,
            SubjectIdentifierMigrationConfirmationRequiredError,
            SubjectIdentifierMigrationStalePlanError,
            migrate_subject_identifiers_for_policy,
        )

        try:
            migrate_subject_identifiers_for_policy(
                study_id=study.pk,
                current_policy=current_policy,
                target_policy=target_policy,
                actor_user_id=command.actor_user_id,
                expected_plan_hash=(
                    command.subject_identifier_migration_plan_hash
                ),
                confirmation_code=(
                    command.subject_identifier_migration_confirmation_code
                ),
            )
        except SubjectIdentifierMigrationBlockedError as exc:
            raise StudySubjectIdentifierMigrationBlockedError(exc.preview) from exc
        except SubjectIdentifierMigrationStalePlanError as exc:
            raise StudySubjectIdentifierMigrationStalePlanError(exc.preview) from exc
        except SubjectIdentifierMigrationConfirmationRequiredError as exc:
            raise StudySubjectIdentifierMigrationRequiredError(exc.preview) from exc

    def _validate_code_unique(self, code, exclude_id):
        if self.repository.study_code_exists(code=code, exclude_id=exclude_id):
            raise StudyCodeAlreadyExistsError(code)

    @staticmethod
    def _build_identifier_policy(command: UpdateStudyCommand):
        return StudySubjectIdentifierPolicy(
            study_id=command.study_id,
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


__all__ = ["UpdateStudyService"]
