from collections import Counter
from dataclasses import dataclass

from django.db import transaction

from apps.audit.public import AuditContextAdapter
from apps.shared.constants import AuditEventAction, AuditEventObjectType
from apps.subject.application.services.early_termination import (
    SubjectEarlyTerminationRequestService,
)
from apps.subject.application.services.event_instance_resync import (
    SubjectEventInstanceResyncResult,
    SubjectEventInstanceResyncService,
)
from apps.subject.infrastructure.repositories.bulk_actions import (
    DjangoSubjectBulkActionRepository,
)


@dataclass(frozen=True)
class SubjectBulkActionResult:
    selected_count: int
    scoped_count: int
    succeeded_count: int
    skipped_count: int
    reason_counts: tuple[tuple[str, int], ...] = ()
    resync_result: SubjectEventInstanceResyncResult | None = None

    @property
    def out_of_scope_count(self) -> int:
        return self.selected_count - self.scoped_count


class SubjectBulkActionService:
    repository_class = DjangoSubjectBulkActionRepository
    resync_service_class = SubjectEventInstanceResyncService
    early_termination_service_class = SubjectEarlyTerminationRequestService
    audit_context_adapter_class = AuditContextAdapter

    def __init__(
        self,
        repository=None,
        resync_service=None,
        early_termination_service=None,
        audit_context_adapter=None,
    ):
        self.repository = repository or self.repository_class()
        self.resync_service = resync_service or self.resync_service_class()
        self.early_termination_service = (
            early_termination_service or self.early_termination_service_class()
        )
        self.audit_context_adapter = (
            audit_context_adapter or self.audit_context_adapter_class()
        )

    @transaction.atomic
    def delete_subjects(
        self,
        *,
        study_id: int,
        site_id: int,
        subject_ids: tuple[int, ...],
        actor_user_id: int | None,
        ip_address: str | None = None,
        user_agent: str = "",
    ) -> SubjectBulkActionResult:
        snapshots = self.repository.list_scoped_subjects_for_update(
            study_id=study_id,
            site_id=site_id,
            subject_ids=subject_ids,
        )
        scoped_ids = tuple(snapshot.subject_id for snapshot in snapshots)
        deleted_count = self.repository.soft_delete_subjects(
            subject_ids=scoped_ids,
            actor_user_id=actor_user_id,
        )
        for snapshot in snapshots:
            before_data = snapshot.as_dict()
            self.audit_context_adapter.record_event(
                action=AuditEventAction.SUBJECT_DELETED,
                object_type=AuditEventObjectType.SUBJECT,
                object_id=str(snapshot.subject_id),
                actor_user_id=actor_user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                before_data=before_data,
                after_data={**before_data, "deleted": True},
            )
        return SubjectBulkActionResult(
            selected_count=len(subject_ids),
            scoped_count=len(scoped_ids),
            succeeded_count=deleted_count,
            skipped_count=len(scoped_ids) - deleted_count,
        )

    def resync_subjects(
        self,
        *,
        study_id: int,
        site_id: int,
        subject_ids: tuple[int, ...],
        actor_user_id: int | None,
    ) -> SubjectBulkActionResult:
        scoped_ids = self._list_scoped_subject_ids(
            study_id=study_id,
            site_id=site_id,
            subject_ids=subject_ids,
        )
        if not scoped_ids:
            return SubjectBulkActionResult(
                selected_count=len(subject_ids),
                scoped_count=0,
                succeeded_count=0,
                skipped_count=0,
            )
        resync_result = self.resync_service.resync_subjects_active_study_version(
            study_id=study_id,
            subject_ids=scoped_ids,
            actor_user_id=actor_user_id,
            trigger_source="subject_list_bulk_resync_stage",
        )
        return SubjectBulkActionResult(
            selected_count=len(subject_ids),
            scoped_count=len(scoped_ids),
            succeeded_count=resync_result.subject_count,
            skipped_count=len(scoped_ids) - resync_result.subject_count,
            resync_result=resync_result,
        )

    @transaction.atomic
    def start_early_termination(
        self,
        *,
        study_id: int,
        site_id: int,
        subject_ids: tuple[int, ...],
        actor_user_id: int | None,
        effective_at,
        reason_code: str,
        reason_text: str,
    ) -> SubjectBulkActionResult:
        scoped_ids = self._list_scoped_subject_ids(
            study_id=study_id,
            site_id=site_id,
            subject_ids=subject_ids,
        )
        reason_counts = Counter()
        succeeded_count = 0
        for subject_id in scoped_ids:
            result = self.early_termination_service.request(
                study_id=study_id,
                subject_id=subject_id,
                actor_user_id=actor_user_id,
                effective_at=effective_at,
                reason_code=reason_code,
                reason_text=reason_text,
            )
            if result.requested:
                succeeded_count += 1
            else:
                reason_counts[result.reason or "unknown"] += 1
        return SubjectBulkActionResult(
            selected_count=len(subject_ids),
            scoped_count=len(scoped_ids),
            succeeded_count=succeeded_count,
            skipped_count=len(scoped_ids) - succeeded_count,
            reason_counts=tuple(sorted(reason_counts.items())),
        )

    def _list_scoped_subject_ids(
        self,
        *,
        study_id: int,
        site_id: int,
        subject_ids: tuple[int, ...],
    ) -> tuple[int, ...]:
        return self.repository.list_scoped_subject_ids(
            study_id=study_id,
            site_id=site_id,
            subject_ids=subject_ids,
        )


__all__ = ["SubjectBulkActionResult", "SubjectBulkActionService"]
