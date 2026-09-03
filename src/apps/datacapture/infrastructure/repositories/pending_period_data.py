from dataclasses import dataclass

from apps.core.choices import DataCapturePageStateStatusChoices
from apps.datacapture.models import DataCapturePageState
from apps.study.models import EventFormBinding


@dataclass(frozen=True)
class PendingPeriodFormState:
    event_instance_id: int
    event_code: str
    event_status: str
    event_form_binding_id: int
    crf_template_id: int
    repeat_index: int
    page_state_id: int | None
    page_status: str


class DjangoPendingPeriodDataRepository:
    DATA_ENTERED_STATUSES = frozenset(
        {
            DataCapturePageStateStatusChoices.SUBMITTED,
            DataCapturePageStateStatusChoices.UNDER_REVIEW,
            DataCapturePageStateStatusChoices.VERIFIED,
            DataCapturePageStateStatusChoices.LOCKED,
            DataCapturePageStateStatusChoices.FINALIZED,
        }
    )

    def list_pending_form_states(
        self,
        *,
        subject_id: int,
        event_instances: tuple[dict, ...],
    ) -> tuple[PendingPeriodFormState, ...]:
        if not event_instances:
            return ()
        event_by_definition_id = {
            int(event["event_definition_id"]): event
            for event in event_instances
        }
        bindings = list(
            EventFormBinding.objects.filter(
                event_definition_id__in=event_by_definition_id,
                deleted=False,
                is_enabled=True,
            )
            .order_by(
                "event_definition__sequence_no",
                "display_order",
                "id",
            )
            .values(
                "id",
                "event_definition_id",
                "form_definition_id",
            )
        )
        event_instance_ids = tuple(
            int(event["event_instance_id"])
            for event in event_instances
        )
        page_states_by_key = {}
        page_states = (
            DataCapturePageState.objects.filter(
                subject_id=subject_id,
                visit_id__in=event_instance_ids,
                event_form_binding_id__in=[
                    binding["id"]
                    for binding in bindings
                ],
                deleted=False,
            )
            .order_by("visit_id", "event_form_binding_id", "repeat_index", "id")
            .values(
                "id",
                "visit_id",
                "event_form_binding_id",
                "repeat_index",
                "status",
            )
        )
        for page_state in page_states:
            key = (
                int(page_state["visit_id"]),
                int(page_state["event_form_binding_id"]),
            )
            page_states_by_key.setdefault(key, []).append(page_state)

        pending_form_states = []
        for binding in bindings:
            event = event_by_definition_id[int(binding["event_definition_id"])]
            key = (
                int(event["event_instance_id"]),
                int(binding["id"]),
            )
            matching_page_states = page_states_by_key.get(key, ())
            if not matching_page_states:
                pending_form_states.append(
                    self._pending_form_state(
                        event=event,
                        binding=binding,
                        page_state=None,
                    )
                )
                continue
            pending_form_states.extend(
                self._pending_form_state(
                    event=event,
                    binding=binding,
                    page_state=page_state,
                )
                for page_state in matching_page_states
                if str(page_state["status"] or "").strip().lower()
                not in self.DATA_ENTERED_STATUSES
            )
        return tuple(pending_form_states)

    @staticmethod
    def _pending_form_state(
        *,
        event,
        binding,
        page_state,
    ) -> PendingPeriodFormState:
        return PendingPeriodFormState(
            event_instance_id=int(event["event_instance_id"]),
            event_code=str(event.get("event_code") or ""),
            event_status=str(event.get("event_status") or ""),
            event_form_binding_id=int(binding["id"]),
            crf_template_id=int(binding["form_definition_id"]),
            repeat_index=int((page_state or {}).get("repeat_index") or 1),
            page_state_id=(
                int(page_state["id"])
                if page_state is not None
                else None
            ),
            page_status=(
                str(page_state["status"])
                if page_state is not None
                else DataCapturePageStateStatusChoices.NOT_STARTED
            ),
        )


__all__ = [
    "DjangoPendingPeriodDataRepository",
    "PendingPeriodFormState",
]
