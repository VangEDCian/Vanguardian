from contextlib import nullcontext
from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.study.domain import StudySubjectIdentifierPolicy, SubjectIdentifierMode
from apps.study.infrastructure.persistence.models import Site, Study
from apps.subject.application.services.identifier_policy_migration import (
    SubjectIdentifierMigrationBlockedError,
    SubjectIdentifierMigrationConfirmationRequiredError,
    SubjectIdentifierMigrationStalePlanError,
    SubjectIdentifierPolicyMigrationService,
    policy_snapshot,
)
from apps.subject.infrastructure.persistence.models import (
    Subject,
    SubjectEnrollment,
    SubjectIdentifierHistory,
    SubjectIdentifierMigrationBatch,
    SubjectRandomization,
)


class SubjectIdentifierPolicyMigrationPreviewTests(SimpleTestCase):
    def setUp(self):
        self.current_policy = _policy(
            SubjectIdentifierMode.GENERATED_AT_ENROLLMENT
        )

    def test_copy_randomization_preview_includes_all_subjects_and_mismatch(self):
        repository = _RepositoryStub(
            rows=(
                _row(
                    subject_id=1,
                    subject_code="NNG31-003",
                    enrolled=True,
                    enrollment_sequence=3,
                    randomization_code="NNG31-006",
                    periods=(_period(11, 1, None), _period(12, 2, None)),
                ),
                _row(
                    subject_id=2,
                    subject_code="NNG31-004",
                    enrolled=False,
                    randomization_code=None,
                ),
            )
        )
        preview = SubjectIdentifierPolicyMigrationService(repository=repository).preview(
            study_id=1,
            current_policy=self.current_policy,
            target_policy=_policy(
                SubjectIdentifierMode.COPY_RANDOMIZATION_AT_RANDOMIZATION
            ),
        )

        self.assertTrue(preview.can_execute)
        self.assertTrue(preview.requires_confirmation)
        self.assertEqual(preview.total_subjects, 2)
        self.assertEqual(preview.changed_subjects, 2)
        self.assertEqual(preview.cleared_subject_codes, 1)
        self.assertEqual(preview.changed_period_kit_codes, 2)
        self.assertEqual(preview.randomized_code_mismatches, 1)
        self.assertEqual(preview.changes[0].to_subject_code, "NNG31-006")
        self.assertEqual(
            [change.to_kit_code for change in preview.changes[0].period_changes],
            ["NNG31-006", "R-NNG31-006"],
        )
        self.assertIsNone(preview.changes[1].to_subject_code)

    def test_non_empty_kit_code_blocks_automatic_migration(self):
        repository = _RepositoryStub(
            rows=(
                _row(
                    subject_id=1,
                    subject_code="NNG31-003",
                    enrolled=True,
                    enrollment_sequence=3,
                    randomization_code="NNG31-006",
                    periods=(_period(11, 1, "NNG31-003"),),
                ),
            )
        )
        preview = SubjectIdentifierPolicyMigrationService(repository=repository).preview(
            study_id=1,
            current_policy=self.current_policy,
            target_policy=_policy(
                SubjectIdentifierMode.COPY_RANDOMIZATION_AT_RANDOMIZATION
            ),
        )

        self.assertFalse(preview.can_execute)
        self.assertIn(
            "assigned_kit_code_requires_reconciliation",
            {issue.code for issue in preview.blockers},
        )

    def test_external_mode_blocks_subject_without_mapping(self):
        preview = SubjectIdentifierPolicyMigrationService(
            repository=_RepositoryStub(rows=(_row(subject_id=1),))
        ).preview(
            study_id=1,
            current_policy=self.current_policy,
            target_policy=_policy(SubjectIdentifierMode.EXTERNAL),
        )

        self.assertFalse(preview.can_execute)
        self.assertEqual(preview.blockers[0].code, "external_subject_code_required")

    def test_duplicate_target_randomization_codes_are_rejected(self):
        rows = (
            _row(subject_id=1, randomization_code="R-001"),
            _row(subject_id=2, randomization_code="R-001"),
        )
        preview = SubjectIdentifierPolicyMigrationService(
            repository=_RepositoryStub(rows=rows)
        ).preview(
            study_id=1,
            current_policy=self.current_policy,
            target_policy=_policy(
                SubjectIdentifierMode.COPY_RANDOMIZATION_AT_RANDOMIZATION
            ),
        )

        self.assertIn(
            "duplicate_subject_code",
            {issue.code for issue in preview.blockers},
        )

    def test_target_code_reserved_by_soft_deleted_subject_is_rejected(self):
        repository = _RepositoryStub(
            rows=(_row(subject_id=1, randomization_code="R-001"),),
            reserved_codes=(
                {"subject_id": 99, "site_id": 1, "subject_code": "R-001"},
            ),
        )
        preview = SubjectIdentifierPolicyMigrationService(
            repository=repository
        ).preview(
            study_id=1,
            current_policy=self.current_policy,
            target_policy=_policy(
                SubjectIdentifierMode.COPY_RANDOMIZATION_AT_RANDOMIZATION
            ),
        )

        self.assertIn(
            "duplicate_subject_code",
            {issue.code for issue in preview.blockers},
        )

    def test_plan_hash_changes_when_subject_state_changes(self):
        repository = _RepositoryStub(rows=(_row(subject_id=1),))
        service = SubjectIdentifierPolicyMigrationService(repository=repository)
        target = _policy(SubjectIdentifierMode.GENERATED_AT_SCREENING)
        first = service.preview(
            study_id=1,
            current_policy=self.current_policy,
            target_policy=target,
        )
        repository.rows = (_row(subject_id=1, subject_code="changed"),)
        second = service.preview(
            study_id=1,
            current_policy=self.current_policy,
            target_policy=target,
        )
        self.assertNotEqual(first.plan_hash, second.plan_hash)


class SubjectIdentifierPolicyMigrationExecutionTests(SimpleTestCase):
    def test_enrolled_subject_requires_hash_and_study_code(self):
        repository = _RepositoryStub(
            rows=(_row(subject_id=1, enrolled=True, enrollment_sequence=1),)
        )
        service = SubjectIdentifierPolicyMigrationService(repository=repository)
        target = _policy(SubjectIdentifierMode.GENERATED_AT_SCREENING)

        with self.assertRaises(SubjectIdentifierMigrationConfirmationRequiredError):
            service.execute(
                study_id=1,
                current_policy=_policy(
                    SubjectIdentifierMode.GENERATED_AT_ENROLLMENT
                ),
                target_policy=target,
                actor_user_id=7,
                expected_plan_hash=None,
                confirmation_code=None,
            )
        self.assertEqual(repository.applied, [])

    def test_stale_hash_is_rejected(self):
        repository = _RepositoryStub(
            rows=(_row(subject_id=1, enrolled=True, enrollment_sequence=1),)
        )
        service = SubjectIdentifierPolicyMigrationService(repository=repository)
        with self.assertRaises(SubjectIdentifierMigrationStalePlanError):
            service.execute(
                study_id=1,
                current_policy=_policy(
                    SubjectIdentifierMode.GENERATED_AT_ENROLLMENT
                ),
                target_policy=_policy(
                    SubjectIdentifierMode.GENERATED_AT_SCREENING
                ),
                actor_user_id=7,
                expected_plan_hash="stale",
                confirmation_code="NNG31",
            )

    def test_confirmed_execution_records_one_batch(self):
        repository = _RepositoryStub(
            rows=(_row(subject_id=1, enrolled=True, enrollment_sequence=1),)
        )
        service = SubjectIdentifierPolicyMigrationService(repository=repository)
        current = _policy(SubjectIdentifierMode.GENERATED_AT_ENROLLMENT)
        target = _policy(SubjectIdentifierMode.GENERATED_AT_SCREENING)
        preview = service.preview(
            study_id=1,
            current_policy=current,
            target_policy=target,
        )
        service.execute(
            study_id=1,
            current_policy=current,
            target_policy=target,
            actor_user_id=7,
            expected_plan_hash=preview.plan_hash,
            confirmation_code="NNG31",
        )

        self.assertEqual(len(repository.created_batches), 1)
        self.assertEqual(len(repository.applied), 1)
        self.assertEqual(repository.applied[0][0].to_subject_code, "NNG31-001")

    def test_blockers_prevent_writes_even_with_confirmation(self):
        repository = _RepositoryStub(
            rows=(_row(subject_id=1, enrolled=True, enrollment_sequence=None),)
        )
        service = SubjectIdentifierPolicyMigrationService(repository=repository)
        current = _policy(SubjectIdentifierMode.GENERATED_AT_SCREENING)
        target = _policy(SubjectIdentifierMode.GENERATED_AT_ENROLLMENT)
        preview = service.preview(
            study_id=1,
            current_policy=current,
            target_policy=target,
        )
        with self.assertRaises(SubjectIdentifierMigrationBlockedError):
            service.execute(
                study_id=1,
                current_policy=current,
                target_policy=target,
                actor_user_id=7,
                expected_plan_hash=preview.plan_hash,
                confirmation_code="NNG31",
            )
        self.assertEqual(repository.created_batches, [])


class SubjectIdentifierPolicyRollbackTests(SimpleTestCase):
    def test_rollback_restores_snapshot_and_derives_new_subject(self):
        old_policy = _policy(SubjectIdentifierMode.GENERATED_AT_SCREENING)
        current_policy = _policy(
            SubjectIdentifierMode.COPY_RANDOMIZATION_AT_RANDOMIZATION
        )
        rows = (
            _row(
                subject_id=1,
                subject_code="R-001",
                randomization_code="R-001",
                enrolled=True,
                enrollment_sequence=1,
            ),
            _row(subject_id=2, current_sequence=2),
        )
        repository = _RepositoryStub(
            rows=rows,
            latest_batch={
                "id": 21,
                "operation_type": "migrate",
                "from_policy": policy_snapshot(old_policy),
                "to_policy": policy_snapshot(current_policy),
                "reverses_batch_id": None,
                "items": (
                    {
                        "subject_id": 1,
                        "from_subject_code": "LEGACY-001",
                        "to_subject_code": "R-001",
                        "periods": (),
                    },
                ),
            },
        )
        preview = SubjectIdentifierPolicyMigrationService(
            repository=repository
        ).preview_rollback(study_id=1, current_policy=current_policy)

        self.assertTrue(preview.can_execute)
        self.assertEqual(preview.rollback_batch_id, 21)
        targets = {change.subject_id: change.to_subject_code for change in preview.changes}
        self.assertEqual(targets[1], "LEGACY-001")
        self.assertEqual(targets[2], "NNG31-002")

    def test_rollback_is_blocked_after_subject_code_changes(self):
        old_policy = _policy(SubjectIdentifierMode.GENERATED_AT_SCREENING)
        current_policy = _policy(
            SubjectIdentifierMode.COPY_RANDOMIZATION_AT_RANDOMIZATION
        )
        repository = _RepositoryStub(
            rows=(_row(subject_id=1, subject_code="MANUAL"),),
            latest_batch={
                "id": 21,
                "operation_type": "migrate",
                "from_policy": policy_snapshot(old_policy),
                "to_policy": policy_snapshot(current_policy),
                "reverses_batch_id": None,
                "items": (
                    {
                        "subject_id": 1,
                        "from_subject_code": "NNG31-001",
                        "to_subject_code": "R-001",
                        "periods": (),
                    },
                ),
            },
        )
        preview = SubjectIdentifierPolicyMigrationService(
            repository=repository
        ).preview_rollback(study_id=1, current_policy=current_policy)
        self.assertIn(
            "subject_code_changed_after_migration",
            {issue.code for issue in preview.blockers},
        )

    def test_rollback_always_requires_preview_confirmation(self):
        old_policy = _policy(SubjectIdentifierMode.GENERATED_AT_SCREENING)
        current_policy = _policy(
            SubjectIdentifierMode.COPY_RANDOMIZATION_AT_RANDOMIZATION
        )
        repository = _RepositoryStub(
            rows=(_row(subject_id=1, subject_code="R-001"),),
            latest_batch={
                "id": 21,
                "operation_type": "migrate",
                "from_policy": policy_snapshot(old_policy),
                "to_policy": policy_snapshot(current_policy),
                "reverses_batch_id": None,
                "items": (
                    {
                        "subject_id": 1,
                        "from_subject_code": "NNG31-001",
                        "to_subject_code": "R-001",
                        "periods": (),
                    },
                ),
            },
        )
        service = SubjectIdentifierPolicyMigrationService(repository=repository)

        with self.assertRaises(SubjectIdentifierMigrationConfirmationRequiredError):
            service.execute_rollback(
                study_id=1,
                current_policy=current_policy,
                actor_user_id=7,
                expected_plan_hash=None,
                confirmation_code=None,
            )


class SubjectIdentifierPolicyMigrationDatabaseTests(TestCase):
    def test_migrate_and_rollback_are_atomic_and_audited(self):
        now = timezone.now()
        study = Study.objects.create(
            created_at=now,
            updated_at=now,
            code="MIGTEST",
            name="Migration Test",
            sponsor="",
            description="",
            is_active=True,
            subject_identifier_mode="generated_at_enrollment",
            screening_identifier_mode="generated",
            subject_code_pattern="{study_code}-{sequence:03d}",
            screening_code_pattern="{study_code}-S{sequence:03d}",
            subject_code_uniqueness_scope="study",
            lock_subject_code_after_assignment=True,
        )
        site = Site.objects.create(
            created_at=now,
            updated_at=now,
            code="S1",
            name="Site 1",
            study_id=study.pk,
            is_active=True,
        )
        randomized = Subject.objects.create(
            created_at=now,
            updated_at=now,
            subject_code="MIGTEST-001",
            screening_code="MIGTEST-S001",
            current_sequence=1,
            enrollment_current_sequence=1,
            site_id=site.pk,
            study_id=study.pk,
        )
        screened = Subject.objects.create(
            created_at=now,
            updated_at=now,
            subject_code="MIGTEST-002",
            screening_code="MIGTEST-S002",
            current_sequence=2,
            site_id=site.pk,
            study_id=study.pk,
        )
        SubjectEnrollment.objects.create(
            created_at=now,
            updated_at=now,
            status="Enrolled",
            is_enrolled=True,
            subject_id=randomized.pk,
            site_id=site.pk,
            study_id=study.pk,
        )
        SubjectRandomization.objects.create(
            created_at=now,
            updated_at=now,
            randomization_number="R-001",
            subject_id=randomized.pk,
            site_id=site.pk,
            study_id=study.pk,
        )
        current = _policy_for_study(
            study,
            SubjectIdentifierMode.GENERATED_AT_ENROLLMENT,
        )
        target = _policy_for_study(
            study,
            SubjectIdentifierMode.COPY_RANDOMIZATION_AT_RANDOMIZATION,
        )
        service = SubjectIdentifierPolicyMigrationService()

        preview = service.preview(
            study_id=study.pk,
            current_policy=current,
            target_policy=target,
        )
        service.execute(
            study_id=study.pk,
            current_policy=current,
            target_policy=target,
            actor_user_id=7,
            expected_plan_hash=preview.plan_hash,
            confirmation_code=study.code,
        )
        randomized.refresh_from_db()
        screened.refresh_from_db()
        self.assertEqual(randomized.subject_code, "R-001")
        self.assertIsNone(screened.subject_code)

        study.subject_identifier_mode = target.subject_identifier_mode
        study.save(update_fields=["subject_identifier_mode"])
        rollback = service.preview_rollback(
            study_id=study.pk,
            current_policy=target,
        )
        service.execute_rollback(
            study_id=study.pk,
            current_policy=target,
            actor_user_id=7,
            expected_plan_hash=rollback.plan_hash,
            confirmation_code=study.code,
        )
        randomized.refresh_from_db()
        screened.refresh_from_db()
        self.assertEqual(randomized.subject_code, "MIGTEST-001")
        self.assertEqual(screened.subject_code, "MIGTEST-002")
        self.assertEqual(SubjectIdentifierMigrationBatch.objects.count(), 2)
        self.assertEqual(SubjectIdentifierHistory.objects.count(), 4)
        self.assertTrue(
            SubjectIdentifierHistory.objects.filter(to_value__isnull=True).exists()
        )


class _RepositoryStub:
    def __init__(self, *, rows=(), latest_batch=None, reserved_codes=()):
        self.rows = tuple(rows)
        self.latest_batch = latest_batch
        self.reserved_codes = tuple(reserved_codes)
        self.created_batches = []
        self.applied = []

    @staticmethod
    def atomic():
        return nullcontext()

    def list_subject_snapshots(self, *, study_id, for_update=False):
        return self.rows

    def list_reserved_subject_codes(self, *, study_id, for_update=False):
        return self.reserved_codes

    def create_batch(self, **kwargs):
        batch = SimpleNamespace(id=len(self.created_batches) + 1, **kwargs)
        self.created_batches.append(batch)
        return batch

    def apply_changes(self, *, batch, changes, actor_user_id):
        self.applied.append(tuple(changes))

    def get_latest_batch_snapshot(self, *, study_id, for_update=False):
        return self.latest_batch


def _policy(mode):
    return StudySubjectIdentifierPolicy(
        study_id=1,
        study_code="NNG31",
        subject_identifier_mode=mode,
        subject_code_pattern="{study_code}-{sequence:03d}",
        subject_code_uniqueness_scope="study",
    )


def _policy_for_study(study, mode):
    return StudySubjectIdentifierPolicy(
        study_id=study.pk,
        study_code=study.code,
        subject_identifier_mode=mode,
        screening_identifier_mode=study.screening_identifier_mode,
        subject_code_pattern=study.subject_code_pattern,
        screening_code_pattern=study.screening_code_pattern,
        subject_code_uniqueness_scope=study.subject_code_uniqueness_scope,
        lock_subject_code_after_assignment=study.lock_subject_code_after_assignment,
    )


def _row(
    *,
    subject_id,
    subject_code=None,
    enrolled=False,
    enrollment_sequence=None,
    randomization_code=None,
    periods=(),
    current_sequence=1,
):
    return {
        "id": subject_id,
        "site_id": 1,
        "site_code": "SITE-01",
        "current_sequence": current_sequence,
        "enrollment_current_sequence": enrollment_sequence,
        "is_enrolled": enrolled,
        "subject_code": subject_code,
        "randomization_code": randomization_code,
        "periods": tuple(periods),
    }


def _period(period_id, period_no, kit_code):
    return {
        "id": period_id,
        "period_no": period_no,
        "status": "Planned",
        "kit_code": kit_code,
    }
