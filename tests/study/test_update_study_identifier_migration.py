from contextlib import nullcontext
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.study.application import (
    StudySubjectIdentifierMigrationRequiredError,
    UpdateStudyCommand,
    UpdateStudyService,
)
from apps.subject.application.services.identifier_policy_migration import (
    SubjectIdentifierMigrationConfirmationRequiredError,
)


class UpdateStudyIdentifierMigrationTests(SimpleTestCase):
    def setUp(self):
        self.study = SimpleNamespace(
            pk=1,
            code="NNG31",
            name="Nanogen 31",
            sponsor="Sponsor",
            description="",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_active=True,
            subject_identifier_mode="generated_at_enrollment",
            screening_identifier_mode="generated",
            subject_code_pattern="{study_code}-{sequence:03d}",
            screening_code_pattern="{study_code}-S{sequence:03d}",
            subject_code_uniqueness_scope="study",
            lock_subject_code_after_assignment=True,
        )
        self.repository = _StudyRepositoryStub(self.study)
        self.service = UpdateStudyService(repository=self.repository)

    def test_policy_change_is_fail_closed_when_confirmation_is_missing(self):
        preview = SimpleNamespace(blockers=())
        source_error = SubjectIdentifierMigrationConfirmationRequiredError(preview)
        with (
            patch(
                "apps.study.application.services.update_study.transaction.atomic",
                return_value=nullcontext(),
            ),
            patch(
                "apps.subject.public.migrate_subject_identifiers_for_policy",
                side_effect=source_error,
            ),
        ):
            with self.assertRaises(
                StudySubjectIdentifierMigrationRequiredError
            ) as raised:
                self.service.execute(_command(mode="generated_at_screening"))

        self.assertIs(raised.exception.preview, preview)
        self.assertEqual(self.repository.saved, [])
        self.assertEqual(
            self.study.subject_identifier_mode,
            "generated_at_enrollment",
        )

    def test_confirmed_policy_change_migrates_before_saving_study(self):
        call_order = []

        def migrate(**kwargs):
            call_order.append("migrate")
            self.assertEqual(kwargs["expected_plan_hash"], "plan-hash")
            self.assertEqual(kwargs["confirmation_code"], "NNG31")

        self.repository.on_save = lambda: call_order.append("save")
        with (
            patch(
                "apps.study.application.services.update_study.transaction.atomic",
                return_value=nullcontext(),
            ),
            patch(
                "apps.subject.public.migrate_subject_identifiers_for_policy",
                side_effect=migrate,
            ),
        ):
            self.service.execute(
                _command(
                    mode="generated_at_screening",
                    plan_hash="plan-hash",
                    confirmation_code="NNG31",
                )
            )

        self.assertEqual(call_order, ["migrate", "save"])
        self.assertEqual(self.study.subject_identifier_mode, "generated_at_screening")

    def test_non_assignment_change_does_not_create_migration_batch(self):
        with (
            patch(
                "apps.study.application.services.update_study.transaction.atomic",
                return_value=nullcontext(),
            ),
            patch(
                "apps.subject.public.migrate_subject_identifiers_for_policy"
            ) as migrate,
        ):
            self.service.execute(_command(name="Renamed"))

        migrate.assert_not_called()
        self.assertEqual(self.study.name, "Renamed")


class _StudyRepositoryStub:
    def __init__(self, study):
        self.study = study
        self.saved = []
        self.on_save = None

    def get_study_for_update(self, *, study_id):
        return self.study

    def get_study(self, *, study_id):
        return self.study

    @staticmethod
    def study_code_exists(*, code, exclude_id=None):
        return False

    @staticmethod
    def touch_study(study, *, actor_user_id):
        study.updated_by_id = actor_user_id

    def save_study(self, study):
        if self.on_save:
            self.on_save()
        self.saved.append(study)
        return study


def _command(
    *,
    mode="generated_at_enrollment",
    name="Nanogen 31",
    plan_hash=None,
    confirmation_code=None,
):
    return UpdateStudyCommand(
        study_id=1,
        code="NNG31",
        name=name,
        sponsor="Sponsor",
        description="",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_active=True,
        actor_user_id=7,
        subject_identifier_mode=mode,
        screening_identifier_mode="generated",
        subject_code_pattern="{study_code}-{sequence:03d}",
        screening_code_pattern="{study_code}-S{sequence:03d}",
        subject_code_uniqueness_scope="study",
        lock_subject_code_after_assignment=True,
        subject_identifier_migration_plan_hash=plan_hash,
        subject_identifier_migration_confirmation_code=confirmation_code,
    )
