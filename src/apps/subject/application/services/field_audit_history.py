from __future__ import annotations

from django.utils.translation import gettext_lazy as _

from apps.subject.infrastructure.repositories.field_audit_history import (
    DjangoSubjectFieldAuditHistoryRepository,
)


class SubjectFieldAuditHistoryQueryService:
    repository_class = DjangoSubjectFieldAuditHistoryRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def get_field_audit_history(
        self,
        *,
        study_id: int,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
        field_template_id: int,
        field_key: str = "",
        event_form_binding_id: int | None = None,
        limit: int = 100,
    ) -> dict | None:
        subject = self.repository.get_subject_context(study_id=study_id, subject_id=subject_id)
        if subject is None:
            return None
        rows = self.repository.list_field_audit_history(
            study_id=study_id,
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
            field_template_id=field_template_id,
            field_key=field_key,
            event_form_binding_id=event_form_binding_id,
            limit=limit,
        )
        return {
            **subject,
            "title": _("AUDIT HISTORY"),
            "rows": rows,
            "total_count": len(rows),
            "field_template_id": field_template_id,
            "field_key": str(field_key or "").strip(),
        }


__all__ = ["SubjectFieldAuditHistoryQueryService"]
