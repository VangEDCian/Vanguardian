from apps.datacapture.infrastructure.repositories.pending_period_data import (
    DjangoPendingPeriodDataRepository,
)


class PendingPeriodDataSnapshotService:
    repository_class = DjangoPendingPeriodDataRepository

    def __init__(self, *, repository=None):
        self.repository = repository or self.repository_class()

    def build_snapshot(
        self,
        *,
        subject_id: int,
        event_instances: tuple[dict, ...],
    ) -> dict:
        pending_forms = self.repository.list_pending_form_states(
            subject_id=subject_id,
            event_instances=event_instances,
        )
        return {
            "pending_form_count": len(pending_forms),
            "pending_forms": [
                {
                    "event_instance_id": form.event_instance_id,
                    "event_code": form.event_code,
                    "event_status": form.event_status,
                    "event_form_binding_id": form.event_form_binding_id,
                    "crf_template_id": form.crf_template_id,
                    "repeat_index": form.repeat_index,
                    "page_state_id": form.page_state_id,
                    "page_status": form.page_status,
                }
                for form in pending_forms
            ],
        }


__all__ = ["PendingPeriodDataSnapshotService"]
