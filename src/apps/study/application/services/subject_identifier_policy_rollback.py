from django.db import transaction

from apps.study.application.exceptions import (
    StudySubjectIdentifierMigrationBlockedError,
    StudySubjectIdentifierMigrationRequiredError,
    StudySubjectIdentifierMigrationStalePlanError,
)
from apps.study.application.queries.study_directory import StudyNotFoundError
from apps.study.application.services.study_audit import StudyAuditService
from apps.study.application.services.update_study import UpdateStudyService
from apps.study.domain import StudySubjectIdentifierPolicy
from apps.study.infrastructure.repositories import DjangoStudyCommandRepository


class RollbackStudySubjectIdentifierPolicyService:
    repository_class = DjangoStudyCommandRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def preview(self, *, study_id):
        study = self.repository.get_study(study_id=study_id)
        if study is None:
            raise StudyNotFoundError(study_id)
        from apps.subject.public import preview_subject_identifier_policy_rollback

        return preview_subject_identifier_policy_rollback(
            study_id=study_id,
            current_policy=UpdateStudyService._build_identifier_policy_from_study(study),
        )

    def execute(
        self,
        *,
        study_id,
        actor_user_id,
        expected_plan_hash,
        confirmation_code,
    ):
        with transaction.atomic():
            study = self.repository.get_study_for_update(study_id=study_id)
            if study is None:
                raise StudyNotFoundError(study_id)
            current_policy = UpdateStudyService._build_identifier_policy_from_study(
                study
            )
            before_data = StudyAuditService.serialize_snapshot(study)
            from apps.subject.public import (
                SubjectIdentifierMigrationBlockedError,
                SubjectIdentifierMigrationConfirmationRequiredError,
                SubjectIdentifierMigrationStalePlanError,
                rollback_subject_identifier_policy,
            )

            try:
                _batch, preview = rollback_subject_identifier_policy(
                    study_id=study_id,
                    current_policy=current_policy,
                    actor_user_id=actor_user_id,
                    expected_plan_hash=expected_plan_hash,
                    confirmation_code=confirmation_code,
                )
            except SubjectIdentifierMigrationBlockedError as exc:
                raise StudySubjectIdentifierMigrationBlockedError(
                    exc.preview
                ) from exc
            except SubjectIdentifierMigrationStalePlanError as exc:
                raise StudySubjectIdentifierMigrationStalePlanError(
                    exc.preview
                ) from exc
            except SubjectIdentifierMigrationConfirmationRequiredError as exc:
                raise StudySubjectIdentifierMigrationRequiredError(
                    exc.preview
                ) from exc

            target = preview.to_policy
            study.subject_identifier_mode = target["subject_identifier_mode"]
            study.subject_code_pattern = target["subject_code_pattern"]
            study.subject_code_uniqueness_scope = target[
                "subject_code_uniqueness_scope"
            ]
            study.lock_subject_code_after_assignment = target[
                "lock_subject_code_after_assignment"
            ]
            self.repository.touch_study(study, actor_user_id=actor_user_id)
            return self.repository.save_study(study), preview, before_data


class PreviewStudySubjectIdentifierPolicyMigrationService:
    repository_class = DjangoStudyCommandRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def execute(self, *, study_id, target_values):
        study = self.repository.get_study(study_id=study_id)
        if study is None:
            raise StudyNotFoundError(study_id)
        target_policy = StudySubjectIdentifierPolicy(
            study_id=study.pk,
            study_code=str(target_values.get("study_code") or study.code).strip(),
            subject_identifier_mode=target_values.get(
                "subject_identifier_mode",
                study.subject_identifier_mode,
            ),
            screening_identifier_mode=target_values.get(
                "screening_identifier_mode",
                study.screening_identifier_mode,
            ),
            subject_code_pattern=target_values.get(
                "subject_code_pattern",
                study.subject_code_pattern,
            ),
            screening_code_pattern=target_values.get(
                "screening_code_pattern",
                study.screening_code_pattern,
            ),
            subject_code_uniqueness_scope=target_values.get(
                "subject_code_uniqueness_scope",
                study.subject_code_uniqueness_scope,
            ),
            lock_subject_code_after_assignment=target_values.get(
                "lock_subject_code_after_assignment",
                study.lock_subject_code_after_assignment,
            ),
        )
        target_policy.validate()
        from apps.subject.public import preview_subject_identifier_policy_migration

        return preview_subject_identifier_policy_migration(
            study_id=study_id,
            current_policy=UpdateStudyService._build_identifier_policy_from_study(
                study
            ),
            target_policy=target_policy,
        )


__all__ = [
    "PreviewStudySubjectIdentifierPolicyMigrationService",
    "RollbackStudySubjectIdentifierPolicyService",
]
