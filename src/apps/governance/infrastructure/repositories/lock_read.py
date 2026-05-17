from apps.governance.models import GovernanceDatabaseLock, GovernanceLockRecord


class DjangoGovernanceLockReadRepository:
    def has_active_database_lock(self) -> bool:
        return GovernanceDatabaseLock.objects.filter(
            deleted=False,
            level="database",
            status="locked",
            unlocked_at__isnull=True,
        ).exists()

    def has_active_scope_lock(
        self,
        *,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
    ) -> bool:
        return GovernanceLockRecord.objects.filter(
            deleted=False,
            status="locked",
            level__in=["page", "form"],
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
            unlocked_at__isnull=True,
        ).exists()

    def is_capture_locked_for_scope(
        self,
        *,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
    ) -> bool:
        if self.has_active_database_lock():
            return True
        return self.has_active_scope_lock(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
        )


__all__ = ["DjangoGovernanceLockReadRepository"]
