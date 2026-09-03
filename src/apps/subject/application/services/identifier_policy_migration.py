from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from apps.study.domain import (
    StudySubjectIdentifierPolicy,
    SubjectCodeUniquenessScope,
    SubjectIdentifierMode,
    SubjectIdentifierPolicyError,
)
from apps.subject.infrastructure.repositories.identifier_policy_migration import (
    DjangoSubjectIdentifierPolicyMigrationRepository,
)

MAX_KIT_CODE_LENGTH = 64


class SubjectIdentifierMigrationError(ValueError):
    pass


class SubjectIdentifierMigrationConfirmationRequiredError(
    SubjectIdentifierMigrationError
):
    def __init__(self, preview):
        self.preview = preview
        super().__init__("Subject identifier migration confirmation is required.")


class SubjectIdentifierMigrationBlockedError(SubjectIdentifierMigrationError):
    def __init__(self, preview):
        self.preview = preview
        super().__init__("Subject identifier migration is blocked by preflight issues.")


class SubjectIdentifierMigrationStalePlanError(SubjectIdentifierMigrationError):
    def __init__(self, preview):
        self.preview = preview
        super().__init__("Subject identifier migration preview is stale.")


@dataclass(frozen=True)
class SubjectIdentifierMigrationIssue:
    code: str
    message: str
    subject_id: int | None = None
    period_id: int | None = None

    def as_dict(self):
        return {
            "code": self.code,
            "message": self.message,
            "subject_id": self.subject_id,
            "period_id": self.period_id,
        }


@dataclass(frozen=True)
class SubjectIdentifierMigrationPeriodChange:
    period_id: int
    period_no: int
    from_kit_code: str | None
    to_kit_code: str | None


@dataclass(frozen=True)
class SubjectIdentifierMigrationChange:
    subject_id: int
    site_id: int
    from_subject_code: str | None
    to_subject_code: str | None
    period_changes: tuple[SubjectIdentifierMigrationPeriodChange, ...] = ()

    @property
    def subject_code_changed(self):
        return self.from_subject_code != self.to_subject_code


@dataclass(frozen=True)
class SubjectIdentifierMigrationPreview:
    study_id: int
    operation_type: str
    from_policy: dict
    to_policy: dict
    plan_hash: str
    total_subjects: int
    enrolled_subjects: int
    randomized_subjects: int
    changed_subjects: int
    cleared_subject_codes: int
    changed_period_kit_codes: int
    randomized_code_mismatches: int
    changes: tuple[SubjectIdentifierMigrationChange, ...] = ()
    blockers: tuple[SubjectIdentifierMigrationIssue, ...] = ()
    warnings: tuple[SubjectIdentifierMigrationIssue, ...] = ()
    rollback_batch_id: int | None = None

    @property
    def can_execute(self):
        return not self.blockers

    @property
    def requires_confirmation(self):
        return self.operation_type == "rollback" or self.enrolled_subjects > 0

    def as_dict(self):
        return {
            "study_id": self.study_id,
            "operation_type": self.operation_type,
            "from_policy": self.from_policy,
            "to_policy": self.to_policy,
            "plan_hash": self.plan_hash,
            "total_subjects": self.total_subjects,
            "enrolled_subjects": self.enrolled_subjects,
            "randomized_subjects": self.randomized_subjects,
            "changed_subjects": self.changed_subjects,
            "cleared_subject_codes": self.cleared_subject_codes,
            "changed_period_kit_codes": self.changed_period_kit_codes,
            "randomized_code_mismatches": self.randomized_code_mismatches,
            "can_execute": self.can_execute,
            "requires_confirmation": self.requires_confirmation,
            "blockers": [issue.as_dict() for issue in self.blockers],
            "warnings": [issue.as_dict() for issue in self.warnings],
            "rollback_batch_id": self.rollback_batch_id,
        }


@dataclass
class _PreviewAccumulator:
    changes: list = field(default_factory=list)
    blockers: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    enrolled_subjects: int = 0
    randomized_subjects: int = 0
    cleared_subject_codes: int = 0
    changed_period_kit_codes: int = 0
    randomized_code_mismatches: int = 0


class SubjectIdentifierPolicyMigrationService:
    repository_class = DjangoSubjectIdentifierPolicyMigrationRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def preview(
        self,
        *,
        study_id: int,
        current_policy: StudySubjectIdentifierPolicy,
        target_policy: StudySubjectIdentifierPolicy,
        for_update: bool = False,
    ) -> SubjectIdentifierMigrationPreview:
        current_policy.validate()
        target_policy.validate()
        rows = self.repository.list_subject_snapshots(
            study_id=study_id,
            for_update=for_update,
        )
        reserved_codes = self.repository.list_reserved_subject_codes(
            study_id=study_id,
            for_update=for_update,
        )
        return self._build_preview(
            study_id=study_id,
            operation_type="migrate",
            current_policy=current_policy,
            target_policy=target_policy,
            rows=rows,
            reserved_codes=reserved_codes,
        )

    def execute(
        self,
        *,
        study_id: int,
        current_policy: StudySubjectIdentifierPolicy,
        target_policy: StudySubjectIdentifierPolicy,
        actor_user_id: int | None,
        expected_plan_hash: str | None,
        confirmation_code: str | None,
    ):
        with self.repository.atomic():
            preview = self.preview(
                study_id=study_id,
                current_policy=current_policy,
                target_policy=target_policy,
                for_update=True,
            )
            self._validate_execution(
                preview=preview,
                expected_plan_hash=expected_plan_hash,
                confirmation_code=confirmation_code,
                study_code=current_policy.study_code,
            )
            batch = self.repository.create_batch(
                study_id=study_id,
                operation_type="migrate",
                from_policy=preview.from_policy,
                to_policy=preview.to_policy,
                plan_hash=preview.plan_hash,
                actor_user_id=actor_user_id,
            )
            self.repository.apply_changes(
                batch=batch,
                changes=preview.changes,
                actor_user_id=actor_user_id,
            )
            return batch, preview

    def preview_rollback(
        self,
        *,
        study_id: int,
        current_policy: StudySubjectIdentifierPolicy,
        for_update: bool = False,
    ) -> SubjectIdentifierMigrationPreview:
        current_policy.validate()
        batch = self.repository.get_latest_batch_snapshot(
            study_id=study_id,
            for_update=for_update,
        )
        if batch is None:
            return self._unavailable_rollback_preview(
                study_id=study_id,
                current_policy=current_policy,
                code="rollback_batch_not_found",
                message="No Subject Code migration is available to roll back.",
            )
        if batch["operation_type"] != "migrate":
            return self._unavailable_rollback_preview(
                study_id=study_id,
                current_policy=current_policy,
                code="latest_batch_not_migration",
                message="Only the latest migration batch can be rolled back.",
                rollback_batch_id=batch["id"],
            )

        target_snapshot = dict(batch["from_policy"])
        # Study Code is managed independently from Subject Code policy rollback.
        # New subjects must use the Study Code that is current at rollback time.
        target_snapshot["study_code"] = current_policy.study_code
        target_policy = policy_from_snapshot(target_snapshot, study_id=study_id)
        rows = self.repository.list_subject_snapshots(
            study_id=study_id,
            for_update=for_update,
        )
        reserved_codes = self.repository.list_reserved_subject_codes(
            study_id=study_id,
            for_update=for_update,
        )
        overrides, stale_issues = self._rollback_overrides(batch=batch, rows=rows)
        preview = self._build_preview(
            study_id=study_id,
            operation_type="rollback",
            current_policy=current_policy,
            target_policy=target_policy,
            rows=rows,
            reserved_codes=reserved_codes,
            target_overrides=overrides,
            extra_blockers=stale_issues,
            rollback_batch_id=batch["id"],
        )
        if policy_snapshot(current_policy) != batch["to_policy"]:
            issue = SubjectIdentifierMigrationIssue(
                code="current_policy_changed",
                message=(
                    "The current Subject Code policy no longer matches the migration "
                    "batch. Rollback requires manual reconciliation."
                ),
            )
            preview = self._with_blocker(preview, issue)
        return preview

    def execute_rollback(
        self,
        *,
        study_id: int,
        current_policy: StudySubjectIdentifierPolicy,
        actor_user_id: int | None,
        expected_plan_hash: str | None,
        confirmation_code: str | None,
    ):
        with self.repository.atomic():
            preview = self.preview_rollback(
                study_id=study_id,
                current_policy=current_policy,
                for_update=True,
            )
            self._validate_execution(
                preview=preview,
                expected_plan_hash=expected_plan_hash,
                confirmation_code=confirmation_code,
                study_code=current_policy.study_code,
            )
            batch = self.repository.create_batch(
                study_id=study_id,
                operation_type="rollback",
                from_policy=preview.from_policy,
                to_policy=preview.to_policy,
                plan_hash=preview.plan_hash,
                actor_user_id=actor_user_id,
                reverses_batch_id=preview.rollback_batch_id,
            )
            self.repository.apply_changes(
                batch=batch,
                changes=preview.changes,
                actor_user_id=actor_user_id,
            )
            return batch, preview

    def _build_preview(
        self,
        *,
        study_id,
        operation_type,
        current_policy,
        target_policy,
        rows,
        reserved_codes=(),
        target_overrides=None,
        extra_blockers=(),
        rollback_batch_id=None,
    ):
        accumulator = _PreviewAccumulator(blockers=list(extra_blockers))
        target_overrides = target_overrides or {}
        desired_codes = []
        for row in rows:
            if row["is_enrolled"]:
                accumulator.enrolled_subjects += 1
            if row["randomization_code"]:
                accumulator.randomized_subjects += 1
                if row["subject_code"] != row["randomization_code"]:
                    accumulator.randomized_code_mismatches += 1

            if row["id"] in target_overrides:
                target_code = target_overrides[row["id"]]
            else:
                target_code = self._resolve_target_code(
                    row=row,
                    policy=target_policy,
                    blockers=accumulator.blockers,
                )
            desired_codes.append((row, target_code))
            change = self._build_change(
                row=row,
                target_code=target_code,
                accumulator=accumulator,
                period_overrides=target_overrides.get(("periods", row["id"]), {}),
            )
            if change.subject_code_changed or change.period_changes:
                accumulator.changes.append(change)

        self._detect_duplicates(
            desired_codes=desired_codes,
            reserved_codes=reserved_codes,
            policy=target_policy,
            blockers=accumulator.blockers,
        )
        if accumulator.enrolled_subjects:
            accumulator.warnings.append(
                SubjectIdentifierMigrationIssue(
                    code="enrolled_subjects_affected",
                    message=(
                        f"{accumulator.enrolled_subjects} enrolled Subject(s) are in scope. "
                        "Previously exported or printed identifiers cannot be recalled."
                    ),
                )
            )
        if accumulator.randomized_code_mismatches:
            accumulator.warnings.append(
                SubjectIdentifierMigrationIssue(
                    code="randomization_code_mismatch",
                    message=(
                        f"{accumulator.randomized_code_mismatches} randomized Subject(s) "
                        "currently have a Subject Code different from Randomization Code."
                    ),
                )
            )

        from_snapshot = policy_snapshot(current_policy)
        to_snapshot = policy_snapshot(target_policy)
        plan_hash = self._plan_hash(
            operation_type=operation_type,
            study_id=study_id,
            from_policy=from_snapshot,
            to_policy=to_snapshot,
            rows=rows,
            reserved_codes=reserved_codes,
            rollback_batch_id=rollback_batch_id,
        )
        return SubjectIdentifierMigrationPreview(
            study_id=study_id,
            operation_type=operation_type,
            from_policy=from_snapshot,
            to_policy=to_snapshot,
            plan_hash=plan_hash,
            total_subjects=len(rows),
            enrolled_subjects=accumulator.enrolled_subjects,
            randomized_subjects=accumulator.randomized_subjects,
            changed_subjects=len(accumulator.changes),
            cleared_subject_codes=accumulator.cleared_subject_codes,
            changed_period_kit_codes=accumulator.changed_period_kit_codes,
            randomized_code_mismatches=accumulator.randomized_code_mismatches,
            changes=tuple(accumulator.changes),
            blockers=tuple(accumulator.blockers),
            warnings=tuple(accumulator.warnings),
            rollback_batch_id=rollback_batch_id,
        )

    @staticmethod
    def _resolve_target_code(*, row, policy, blockers):
        mode = policy.normalized_subject_identifier_mode
        try:
            if mode is SubjectIdentifierMode.GENERATED_AT_SCREENING:
                return policy.generate_subject_code_for_sequence(
                    sequence=row["current_sequence"],
                    site_code=row["site_code"],
                )
            if mode is SubjectIdentifierMode.GENERATED_AT_ENROLLMENT:
                if not row["is_enrolled"]:
                    return None
                if row["enrollment_current_sequence"] is None:
                    blockers.append(
                        SubjectIdentifierMigrationIssue(
                            code="missing_enrollment_sequence",
                            message="Enrolled Subject is missing its enrollment sequence.",
                            subject_id=row["id"],
                        )
                    )
                    return row["subject_code"]
                return policy.generate_subject_code_for_sequence(
                    sequence=row["enrollment_current_sequence"],
                    site_code=row["site_code"],
                )
            if mode is SubjectIdentifierMode.COPY_RANDOMIZATION_AT_RANDOMIZATION:
                return row["randomization_code"]
            if row["subject_code"] is None:
                blockers.append(
                    SubjectIdentifierMigrationIssue(
                        code="external_subject_code_required",
                        message=(
                            "External mode requires a Subject Code mapping for every "
                            "existing Subject."
                        ),
                        subject_id=row["id"],
                    )
                )
            return row["subject_code"]
        except SubjectIdentifierPolicyError as exc:
            blockers.append(
                SubjectIdentifierMigrationIssue(
                    code="subject_code_generation_failed",
                    message=str(exc),
                    subject_id=row["id"],
                )
            )
            return row["subject_code"]

    def _build_change(
        self,
        *,
        row,
        target_code,
        accumulator,
        period_overrides,
    ):
        period_changes = []
        subject_code_changed = row["subject_code"] != target_code
        if subject_code_changed and row["subject_code"] and target_code is None:
            accumulator.cleared_subject_codes += 1
        if subject_code_changed:
            for period in row["periods"]:
                target_kit_code = period_overrides.get(
                    period["id"],
                    self._build_kit_code(target_code, period["period_no"]),
                )
                if target_kit_code == period["kit_code"]:
                    continue
                if period["kit_code"] is not None:
                    accumulator.blockers.append(
                        SubjectIdentifierMigrationIssue(
                            code="assigned_kit_code_requires_reconciliation",
                            message=(
                                "A non-empty Kit Code would change. The system cannot "
                                "verify whether its physical label has been issued."
                            ),
                            subject_id=row["id"],
                            period_id=period["id"],
                        )
                    )
                if target_kit_code and len(target_kit_code) > MAX_KIT_CODE_LENGTH:
                    accumulator.blockers.append(
                        SubjectIdentifierMigrationIssue(
                            code="kit_code_too_long",
                            message=(
                                f"Generated Kit Code exceeds {MAX_KIT_CODE_LENGTH} characters."
                            ),
                            subject_id=row["id"],
                            period_id=period["id"],
                        )
                    )
                    continue
                accumulator.changed_period_kit_codes += 1
                period_changes.append(
                    SubjectIdentifierMigrationPeriodChange(
                        period_id=period["id"],
                        period_no=period["period_no"],
                        from_kit_code=period["kit_code"],
                        to_kit_code=target_kit_code,
                    )
                )
        return SubjectIdentifierMigrationChange(
            subject_id=row["id"],
            site_id=row["site_id"],
            from_subject_code=row["subject_code"],
            to_subject_code=target_code,
            period_changes=tuple(period_changes),
        )

    @staticmethod
    def _detect_duplicates(*, desired_codes, reserved_codes, policy, blockers):
        seen = {}
        scope = policy.normalized_uniqueness_scope
        for reserved in reserved_codes:
            code = reserved["subject_code"]
            if code is None:
                continue
            key = (
                code
                if scope is SubjectCodeUniquenessScope.STUDY
                else (reserved["site_id"], code)
            )
            seen[key] = reserved["subject_id"]
        for row, code in desired_codes:
            if code is None:
                continue
            key = (
                code
                if scope is SubjectCodeUniquenessScope.STUDY
                else (row["site_id"], code)
            )
            previous_subject_id = seen.get(key)
            if previous_subject_id is not None:
                blockers.append(
                    SubjectIdentifierMigrationIssue(
                        code="duplicate_subject_code",
                        message=(
                            f"Target Subject Code {code!r} conflicts with Subject "
                            f"{previous_subject_id}."
                        ),
                        subject_id=row["id"],
                    )
                )
            else:
                seen[key] = row["id"]

    @staticmethod
    def _build_kit_code(subject_code, period_no):
        if not subject_code:
            return None
        if int(period_no) == 1:
            return subject_code
        if int(period_no) == 2:
            return f"R-{subject_code}"
        return f"P{period_no}-{subject_code}"

    @staticmethod
    def _plan_hash(
        *,
        operation_type,
        study_id,
        from_policy,
        to_policy,
        rows,
        reserved_codes,
        rollback_batch_id,
    ):
        payload = {
            "operation_type": operation_type,
            "study_id": study_id,
            "from_policy": from_policy,
            "to_policy": to_policy,
            "rollback_batch_id": rollback_batch_id,
            "subjects": rows,
            "reserved_subject_codes": reserved_codes,
        }
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _rollback_overrides(*, batch, rows):
        rows_by_id = {row["id"]: row for row in rows}
        overrides = {}
        blockers = []
        for item in batch["items"]:
            row = rows_by_id.get(item["subject_id"])
            if row is None:
                blockers.append(
                    SubjectIdentifierMigrationIssue(
                        code="migrated_subject_missing",
                        message="A Subject from the migration batch no longer exists.",
                        subject_id=item["subject_id"],
                    )
                )
                continue
            if row["subject_code"] != item["to_subject_code"]:
                blockers.append(
                    SubjectIdentifierMigrationIssue(
                        code="subject_code_changed_after_migration",
                        message="Subject Code changed after the migration batch.",
                        subject_id=item["subject_id"],
                    )
                )
            overrides[item["subject_id"]] = item["from_subject_code"]
            row_periods = {period["id"]: period for period in row["periods"]}
            period_overrides = {}
            for period_item in item["periods"]:
                period = row_periods.get(period_item["period_id"])
                if period is None or period["kit_code"] != period_item["to_kit_code"]:
                    blockers.append(
                        SubjectIdentifierMigrationIssue(
                            code="kit_code_changed_after_migration",
                            message="Kit Code changed after the migration batch.",
                            subject_id=item["subject_id"],
                            period_id=period_item["period_id"],
                        )
                    )
                    continue
                period_overrides[period_item["period_id"]] = period_item[
                    "from_kit_code"
                ]
            overrides[("periods", item["subject_id"])] = period_overrides
        return overrides, blockers

    @staticmethod
    def _validate_execution(
        *, preview, expected_plan_hash, confirmation_code, study_code
    ):
        if preview.blockers:
            raise SubjectIdentifierMigrationBlockedError(preview)
        if preview.requires_confirmation and not expected_plan_hash:
            raise SubjectIdentifierMigrationConfirmationRequiredError(preview)
        if expected_plan_hash and expected_plan_hash != preview.plan_hash:
            raise SubjectIdentifierMigrationStalePlanError(preview)
        if preview.requires_confirmation and str(confirmation_code or "").strip() != str(
            study_code
        ).strip():
            raise SubjectIdentifierMigrationConfirmationRequiredError(preview)

    @staticmethod
    def _with_blocker(preview, issue):
        return SubjectIdentifierMigrationPreview(
            **{
                **preview.__dict__,
                "blockers": (*preview.blockers, issue),
            }
        )

    @staticmethod
    def _unavailable_rollback_preview(
        *, study_id, current_policy, code, message, rollback_batch_id=None
    ):
        snapshot = policy_snapshot(current_policy)
        return SubjectIdentifierMigrationPreview(
            study_id=study_id,
            operation_type="rollback",
            from_policy=snapshot,
            to_policy=snapshot,
            plan_hash="",
            total_subjects=0,
            enrolled_subjects=0,
            randomized_subjects=0,
            changed_subjects=0,
            cleared_subject_codes=0,
            changed_period_kit_codes=0,
            randomized_code_mismatches=0,
            blockers=(SubjectIdentifierMigrationIssue(code=code, message=message),),
            rollback_batch_id=rollback_batch_id,
        )


def policy_snapshot(policy: StudySubjectIdentifierPolicy):
    return {
        "study_code": policy.study_code,
        "subject_identifier_mode": str(policy.subject_identifier_mode),
        "screening_identifier_mode": str(policy.screening_identifier_mode),
        "subject_code_pattern": policy.subject_code_pattern,
        "screening_code_pattern": policy.screening_code_pattern,
        "subject_code_uniqueness_scope": str(policy.subject_code_uniqueness_scope),
        "lock_subject_code_after_assignment": bool(
            policy.lock_subject_code_after_assignment
        ),
    }


def policy_from_snapshot(snapshot, *, study_id):
    return StudySubjectIdentifierPolicy(study_id=study_id, **snapshot)


__all__ = [
    "SubjectIdentifierMigrationBlockedError",
    "SubjectIdentifierMigrationChange",
    "SubjectIdentifierMigrationConfirmationRequiredError",
    "SubjectIdentifierMigrationError",
    "SubjectIdentifierMigrationIssue",
    "SubjectIdentifierMigrationPeriodChange",
    "SubjectIdentifierMigrationPreview",
    "SubjectIdentifierMigrationStalePlanError",
    "SubjectIdentifierPolicyMigrationService",
    "policy_from_snapshot",
    "policy_snapshot",
]
