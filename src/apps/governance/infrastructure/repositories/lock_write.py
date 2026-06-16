from django.utils import timezone

from apps.governance.models import GovernanceLockRecord


class DjangoGovernanceLockWriteRepository:
    def lock_page_scope(
        self,
        *,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
        page_state_id: int,
        actor_user_id: int | None = None,
        reason: str | None = None,
    ) -> int:
        existing = (
            GovernanceLockRecord.objects.filter(
                deleted=False,
                status="locked",
                level="page",
                subject_id=subject_id,
                visit_id=visit_id,
                crf_template_id=crf_template_id,
                unlocked_at__isnull=True,
            )
            .order_by("id")
            .first()
        )
        if existing is not None:
            return int(existing.pk)

        now = timezone.now()
        record = GovernanceLockRecord.objects.create(
            created_at=now,
            updated_at=now,
            deleted=False,
            status="locked",
            level="page",
            reason=(reason or "Page locked").strip(),
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
            page_state_id=page_state_id,
            locked_at=now,
            locked_by_id=actor_user_id,
        )
        return int(record.pk)


__all__ = ["DjangoGovernanceLockWriteRepository"]
