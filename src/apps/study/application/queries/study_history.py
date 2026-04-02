import json

from django.utils.translation import gettext_lazy as _

from apps.audit.infrastructure.persistence.models import AuditEvent
from apps.shared.constants.audit_events import AuditEventAction, AuditEventObjectType


class StudyHistoryQueryService:
    _action_labels = {
        AuditEventAction.STUDY_CREATED: _("Created"),
        AuditEventAction.STUDY_UPDATED: _("Updated"),
        AuditEventAction.STUDY_STATUS_CHANGED: _("Status changed"),
    }

    def list_events(self, *, study_id):
        events = (
            AuditEvent.objects.filter(
                object_type=AuditEventObjectType.STUDY,
                object_id=str(study_id),
                deleted=False,
            )
            .select_related("created_by")
            .order_by("-created_at")
        )

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
