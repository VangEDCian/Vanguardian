import json

from django.utils.translation import gettext_lazy as _

from apps.shared.constants.audit_events import AuditEventAction
from apps.study.infrastructure.repositories import DjangoStudyDirectoryRepository


class StudyHistoryQueryService:
    repository_class = DjangoStudyDirectoryRepository
    _action_labels = {
        AuditEventAction.STUDY_CREATED: _("Created"),
        AuditEventAction.STUDY_UPDATED: _("Updated"),
        AuditEventAction.STUDY_STATUS_CHANGED: _("Status changed"),
        AuditEventAction.STUDY_DELETED: _("Deleted"),
    }

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def list_events(self, *, study_id):
        events = self.repository.list_study_history_events(study_id=study_id)

        return {
            "history_rows": [self._build_row(event) for event in events],
            "history_empty_text": _("No history recorded for this study yet."),
        }

    def _build_row(self, event):
        before = json.loads(event.before_data or "{}")
        after = json.loads(event.after_data or "{}")
        actor = event.created_by

        return {
            "timestamp": event.created_at,
            "action_label": self._action_labels.get(event.action, event.action),
            "actor": actor.username if actor else "—",
            "changes": self._build_changes(before, after),
        }

    @staticmethod
    def _build_changes(before, after):
        changes = []
        all_keys = set(before.keys()) | set(after.keys())
        for key in sorted(all_keys):
            before_val = before.get(key)
            after_val = after.get(key)
            if before_val != after_val:
                changes.append({
                    "field": key,
                    "before": "—" if before_val is None else str(before_val),
                    "after": "—" if after_val is None else str(after_val),
                })
        return changes
