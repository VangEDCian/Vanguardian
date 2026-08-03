from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from apps.subject.infrastructure.persistence.models import (
    Subject,
    SubjectIdentifierHistory,
    SubjectIdentifierMigrationBatch,
    SubjectIdentifierMigrationItem,
    SubjectIdentifierMigrationPeriodItem,
    SubjectPeriod,
)


class DjangoSubjectIdentifierPolicyMigrationRepository:
    atomic = staticmethod(transaction.atomic)

    def list_subject_snapshots(self, *, study_id: int, for_update: bool = False):
        queryset = Subject.objects.filter(study_id=study_id, deleted=False)
        if for_update:
            queryset = queryset.select_for_update()
        period_queryset = SubjectPeriod.objects.all()
        if for_update:
            period_queryset = period_queryset.select_for_update()
        subjects = list(
            queryset.select_related("site", "enrollment", "randomization")
            .prefetch_related(Prefetch("periods", queryset=period_queryset))
            .order_by("id")
        )
        snapshots = []
        for subject in subjects:
            enrollment = getattr(subject, "enrollment", None)
            randomization = getattr(subject, "randomization", None)
            periods = tuple(
                {
                    "id": period.pk,
                    "period_no": period.period_no,
                    "status": period.status,
                    "kit_code": self._normalize(period.kit_code),
                }
                for period in sorted(
                    (period for period in subject.periods.all() if not period.deleted),
                    key=lambda period: (period.period_no, period.pk),
                )
            )
            snapshots.append(
                {
                    "id": subject.pk,
                    "site_id": subject.site_id,
                    "site_code": subject.site.code,
                    "current_sequence": subject.current_sequence,
                    "enrollment_current_sequence": subject.enrollment_current_sequence,
                    "is_enrolled": bool(
                        enrollment
                        and not enrollment.deleted
                        and enrollment.is_enrolled
                    ),
                    "subject_code": self._normalize(subject.subject_code),
                    "randomization_code": self._normalize(
                        randomization.randomization_number
                        if randomization and not randomization.deleted
                        else None
                    ),
                    "periods": periods,
                }
            )
        return tuple(snapshots)

    def create_batch(
        self,
        *,
        study_id: int,
        operation_type: str,
        from_policy: dict,
        to_policy: dict,
        plan_hash: str,
        actor_user_id: int | None,
        reverses_batch_id: int | None = None,
    ):
        return SubjectIdentifierMigrationBatch.objects.create(
            study_id=study_id,
            operation_type=operation_type,
            from_policy_json=from_policy,
            to_policy_json=to_policy,
            plan_hash=plan_hash,
            reverses_batch_id=reverses_batch_id,
            occurred_at=timezone.now(),
            actor_user_id=actor_user_id,
        )

    def list_reserved_subject_codes(
        self,
        *,
        study_id: int,
        for_update: bool = False,
    ):
        queryset = Subject.objects.filter(
            study_id=study_id,
            deleted=True,
            subject_code__isnull=False,
        )
        if for_update:
            queryset = queryset.select_for_update()
        return tuple(
            {
                "subject_id": row["id"],
                "site_id": row["site_id"],
                "subject_code": self._normalize(row["subject_code"]),
            }
            for row in queryset.values("id", "site_id", "subject_code").order_by(
                "id"
            )
        )

    def apply_changes(self, *, batch, changes, actor_user_id: int | None):
        changed_subjects = [change for change in changes if change.subject_code_changed]
        changed_subject_ids = [change.subject_id for change in changed_subjects]
        now = timezone.now()

        # Clear first so code swaps cannot violate the database uniqueness key.
        if changed_subject_ids:
            Subject.objects.filter(pk__in=changed_subject_ids).update(
                subject_code=None,
                updated_at=now,
                updated_by_id=actor_user_id,
            )

        for change in changes:
            item = SubjectIdentifierMigrationItem.objects.create(
                migration_batch=batch,
                subject_id=change.subject_id,
                from_subject_code=change.from_subject_code,
                to_subject_code=change.to_subject_code,
            )
            if change.subject_code_changed:
                Subject.objects.filter(pk=change.subject_id).update(
                    subject_code=change.to_subject_code,
                    updated_at=now,
                    updated_by_id=actor_user_id,
                )
                SubjectIdentifierHistory.objects.create(
                    subject_id=change.subject_id,
                    identifier_type="subject_code",
                    from_value=change.from_subject_code,
                    to_value=change.to_subject_code,
                    assignment_source=(
                        "policy_rollback"
                        if batch.operation_type == "rollback"
                        else "policy_migration"
                    ),
                    occurred_at=now,
                    actor_user_id=actor_user_id,
                )

            for period_change in change.period_changes:
                SubjectIdentifierMigrationPeriodItem.objects.create(
                    migration_item=item,
                    period_id=period_change.period_id,
                    from_kit_code=period_change.from_kit_code,
                    to_kit_code=period_change.to_kit_code,
                )
                SubjectPeriod.objects.filter(pk=period_change.period_id).update(
                    kit_code=period_change.to_kit_code,
                    updated_at=now,
                    updated_by_id=actor_user_id,
                )

    def get_latest_batch_snapshot(self, *, study_id: int, for_update: bool = False):
        queryset = SubjectIdentifierMigrationBatch.objects.filter(study_id=study_id)
        if for_update:
            queryset = queryset.select_for_update()
        batch = queryset.order_by("-occurred_at", "-id").first()
        if batch is None:
            return None
        items = []
        for item in batch.items.prefetch_related("period_items").order_by("id"):
            items.append(
                {
                    "subject_id": item.subject_id,
                    "from_subject_code": self._normalize(item.from_subject_code),
                    "to_subject_code": self._normalize(item.to_subject_code),
                    "periods": tuple(
                        {
                            "period_id": period_item.period_id,
                            "from_kit_code": self._normalize(period_item.from_kit_code),
                            "to_kit_code": self._normalize(period_item.to_kit_code),
                        }
                        for period_item in item.period_items.order_by("id")
                    ),
                }
            )
        return {
            "id": batch.pk,
            "operation_type": batch.operation_type,
            "from_policy": batch.from_policy_json,
            "to_policy": batch.to_policy_json,
            "reverses_batch_id": batch.reverses_batch_id,
            "items": tuple(items),
        }

    @staticmethod
    def _normalize(value):
        normalized = str(value or "").strip()
        return normalized or None


__all__ = ["DjangoSubjectIdentifierPolicyMigrationRepository"]
