from django.urls import reverse
from django.utils import timezone
from django.utils.translation import get_language
from django.utils.translation import gettext as _

from apps.core.choices.study import EventExecutionModeChoices, EventInstanceStatusChoices
from apps.crf.application.services.crf_template_query import CrfTemplateQueryService
from apps.crf.public import CrfContextAdapter
from apps.datacapture.domain import DataCapturePageState
from apps.datacapture.public import (
    list_form_instances_for_event_instance as _list_form_instances_for_event_instance,
)
from apps.datacapture.public import list_form_instances_for_event_instances
from apps.reconcile.public import summarize_reconcile_workbench_for_page_states
from apps.shared.datetime_formatting import date_format
from apps.study.models import EventFormBinding
from apps.subject.models import SubjectEventInstance


def list_form_instances_for_event_instance(*, visit_id: int, language_code: str | None = None):
    return _list_form_instances_for_event_instance(
        visit_id=visit_id,
        language_code=language_code,
    )


_DEFAULT_LIST_FORM_INSTANCES_FOR_EVENT_INSTANCE = list_form_instances_for_event_instance


class SubjectDetailNavigationMixin:
    crf_context_adapter_class = CrfContextAdapter

    def _build_event_navigation(self):
        event_instances = list(
            SubjectEventInstance.objects.filter(
                subject_id=self.object.pk,
                deleted=False,
                event_definition__execution_mode=EventExecutionModeChoices.FORM_ENTRY,
            )
            .exclude(status=EventInstanceStatusChoices.NOT_READY)
            .select_related("event_definition")
            .order_by("event_definition__sequence_no", "repeat_index", "id")
        )

        event_definition_ids = [item.event_definition_id for item in event_instances]
        bindings = list(
            EventFormBinding.objects.filter(
                study_id=self.object.study_id,
                deleted=False,
                is_enabled=True,
                event_definition_id__in=event_definition_ids,
            )
            .select_related("form_definition")
            .prefetch_related("form_definition__translations")
            .order_by("event_definition__sequence_no", "display_order", "id")
        )

        bindings_map = {}
        for binding in bindings:
            bindings_map.setdefault(binding.event_definition_id, []).append(binding)

        repeat_rule_instances = list(
            SubjectEventInstance.objects.filter(
                subject_id=self.object.pk,
                event_definition_id__in=event_definition_ids,
                deleted=False,
            ).only("id", "event_definition_id", "status")
        )
        event_definition_counts = {}
        open_event_definition_ids = set()
        for event_instance in repeat_rule_instances:
            event_definition_counts[event_instance.event_definition_id] = (
                event_definition_counts.get(event_instance.event_definition_id, 0) + 1
            )
            if event_instance.status == EventInstanceStatusChoices.OPEN:
                open_event_definition_ids.add(event_instance.event_definition_id)

        last_visible_event_instance_id_by_definition = {}
        for event_instance in event_instances:
            last_visible_event_instance_id_by_definition[event_instance.event_definition_id] = (
                event_instance.pk
            )

        language_code = get_language()
        lang = CrfTemplateQueryService._normalize_language_code(language_code)
        event_items_by_definition = {}
        if list_form_instances_for_event_instance is not _DEFAULT_LIST_FORM_INSTANCES_FOR_EVENT_INSTANCE:
            form_instances_by_event_id = {
                int(event_instance.pk): list_form_instances_for_event_instance(
                    visit_id=int(event_instance.pk),
                    language_code=language_code,
                )
                for event_instance in event_instances
            }
        else:
            form_instances_by_event_id = list_form_instances_for_event_instances(
                visit_ids=tuple(int(event_instance.pk) for event_instance in event_instances),
                language_code=language_code,
            )
        for event_instance in event_instances:
            form_instance_labels_by_binding_id = {}
            form_instance_state_by_binding_id = {}
            for form_instance in form_instances_by_event_id.get(int(event_instance.pk), []):
                binding_id = int(form_instance.event_form_binding_id)
                form_instance_labels_by_binding_id.setdefault(
                    binding_id,
                    str(form_instance.display_label or "").strip(),
                )
                form_instance_state_by_binding_id.setdefault(
                    binding_id,
                    {
                        "page_state_id": getattr(form_instance, "page_state_id", None),
                        "status": str(getattr(form_instance, "status", "") or ""),
                    },
                )
            forms = []
            for binding in bindings_map.get(event_instance.event_definition_id, []):
                template = binding.form_definition
                template_name = CrfTemplateQueryService._translated_value(
                    template,
                    lang,
                    "name",
                    default=template.code,
                )
                form_title = (
                    form_instance_labels_by_binding_id.get(int(binding.pk))
                    or template_name
                )
                form_state = form_instance_state_by_binding_id.get(int(binding.pk), {})
                page_state_id = form_state.get("page_state_id")
                page_state_status = str(form_state.get("status") or "").strip().lower()
                forms.append(
                    {
                        "id": str(binding.pk),
                        "form_definition_id": str(template.pk),
                        "title": form_title,
                        "code": template.code,
                        "page_state_id": str(page_state_id or ""),
                        "page_state_status": page_state_status,
                        "sidebar_tone": self._resolve_form_sidebar_tone(
                            page_state_id=page_state_id,
                            page_state_status=page_state_status,
                        ),
                    }
                )

            event_definition = event_instance.event_definition
            event_name = event_instance.event_name_snapshot or event_definition.name
            event_count = event_definition_counts.get(event_instance.event_definition_id, 0)
            max_repeats = event_definition.max_repeats
            is_last_repeat_instance = (
                last_visible_event_instance_id_by_definition.get(event_instance.event_definition_id)
                == event_instance.pk
            )
            can_add_another = self._can_add_another_repeating_event(
                is_repeating=event_definition.is_repeating,
                is_last_repeat_instance=is_last_repeat_instance,
                has_open_event_instance=event_instance.event_definition_id in open_event_definition_ids,
                event_count=event_count,
                max_repeats=max_repeats,
            )
            event_items_by_definition.setdefault(event_instance.event_definition_id, []).append(
                self._build_event_navigation_item(
                    event_instance=event_instance,
                    event_definition=event_definition,
                    event_name=event_name,
                    forms=forms,
                    can_add_another=can_add_another,
                ),
            )
        return self._collapse_repeating_event_navigation(event_items_by_definition)

    def _build_event_navigation_item(
        self,
        *,
        event_instance,
        event_definition,
        event_name: str,
        forms: list[dict],
        can_add_another: bool,
    ) -> dict:
        return {
            "id": str(event_instance.pk),
            "event_definition_id": str(event_instance.event_definition_id),
            "code": event_instance.event_code_snapshot or event_definition.code,
            "name": event_name,
            "status": event_instance.status,
            "repeat_index": event_instance.repeat_index,
            "is_repeating": event_definition.is_repeating,
            "can_add_another": can_add_another,
            "add_another_label": _("Add Another %(event_name)s") % {"event_name": event_name},
            "completed_at_label": self._format_completed_at_label(event_instance.completed_at),
            "sidebar_label": self._resolve_repeating_sidebar_label(
                forms=forms,
                completed_at=event_instance.completed_at,
            ),
            "forms": forms,
            "repeat_event_instances": [],
        }

    @classmethod
    def _resolve_repeating_sidebar_label(cls, *, forms: list[dict], completed_at) -> str:
        for form in forms or []:
            title = str(form.get("title") or "").strip()
            if title:
                return title
        return cls._format_completed_at_label(completed_at)

    @staticmethod
    def _collapse_repeating_event_navigation(event_items_by_definition: dict[int, list[dict]]) -> list[dict]:
        payload = []
        for event_items in event_items_by_definition.values():
            if not event_items:
                continue
            if not event_items[0].get("is_repeating"):
                payload.extend(event_items)
                continue

            primary_item = next(
                (
                    event_item
                    for event_item in event_items
                    if event_item.get("status") == EventInstanceStatusChoices.OPEN
                ),
                event_items[-1],
            )
            repeat_event_instances = [
                event_item
                for event_item in event_items
                if event_item.get("status") == EventInstanceStatusChoices.COMPLETED
            ]
            payload.append(
                {
                    **primary_item,
                    "repeat_event_instances": repeat_event_instances,
                }
            )
        return payload

    @staticmethod
    def _resolve_form_sidebar_tone(*, page_state_id: int | None, page_state_status: str) -> str:
        if page_state_id:
            summary = summarize_reconcile_workbench_for_page_states(
                page_state_ids=(int(page_state_id),),
            )
            if int(summary.get("validation_issues_open") or 0) > 0 or int(summary.get("open") or 0) > 0:
                return "danger"
        if page_state_status == DataCapturePageState.SUBMITTED:
            return "success"
        return ""

    @staticmethod
    def _resolve_default_focus_event(event_navigation: list[dict]) -> dict | None:
        for event_item in event_navigation:
            if event_item.get("status") == EventInstanceStatusChoices.OPEN:
                return event_item
            for repeat_item in event_item.get("repeat_event_instances") or []:
                if repeat_item.get("status") == EventInstanceStatusChoices.OPEN:
                    return repeat_item
        return event_navigation[0] if event_navigation else None

    @staticmethod
    def _resolve_focus(items, focus_id):
        if not items:
            return None
        for item in items:
            if item["id"] == focus_id:
                return item
            for repeat_item in item.get("repeat_event_instances") or []:
                if repeat_item["id"] == focus_id:
                    return repeat_item
        return items[0]

    @staticmethod
    def _can_add_another_repeating_event(
        *,
        is_repeating: bool,
        is_last_repeat_instance: bool,
        has_open_event_instance: bool,
        event_count: int,
        max_repeats: int | None,
    ) -> bool:
        if not is_repeating or not is_last_repeat_instance or has_open_event_instance:
            return False
        return max_repeats is None or event_count < max_repeats

    @staticmethod
    def _format_completed_at_label(value) -> str:
        if value in (None, ""):
            return "—"
        if getattr(value, "tzinfo", None) is not None:
            value = timezone.localtime(value)
        return date_format(value, "DATE_FORMAT")

    def _with_focus_urls(self, event_navigation):
        detail_url = reverse(
            "subject:subject_detail",
            kwargs={
                "study_id": self.get_study_id(),
                "subject_id": self.object.pk,
            },
        )
        payload = []
        for event_item in event_navigation:
            add_another_url = self._build_add_another_url(event_item)
            forms_with_url = [
                {
                    **form_item,
                    "focus_url": f"{detail_url}?event={event_item['id']}&form={form_item['id']}",
                }
                for form_item in event_item["forms"]
            ]
            payload.append(
                {
                    **event_item,
                    "focus_url": f"{detail_url}?event={event_item['id']}",
                    "add_another_url": add_another_url,
                    "forms": forms_with_url,
                    "repeat_event_instances": self._with_repeat_event_focus_urls(
                        repeat_event_instances=event_item.get("repeat_event_instances") or [],
                        detail_url=detail_url,
                        add_another_url=add_another_url,
                    ),
                },
            )
        return payload

    def _build_add_another_url(self, event_item: dict) -> str:
        if not event_item.get("can_add_another"):
            return ""
        return reverse(
            "subject:subject_eventinstance_add_another",
            kwargs={
                "study_id": self.get_study_id(),
                "subject_id": self.object.pk,
                "event_definition_id": event_item["event_definition_id"],
            },
        )

    @staticmethod
    def _with_repeat_event_focus_urls(
        *,
        repeat_event_instances: list[dict],
        detail_url: str,
        add_another_url: str,
    ) -> list[dict]:
        payload = []
        for repeat_item in repeat_event_instances:
            forms_with_url = [
                {
                    **form_item,
                    "focus_url": f"{detail_url}?event={repeat_item['id']}&form={form_item['id']}",
                }
                for form_item in repeat_item["forms"]
            ]
            payload.append(
                {
                    **repeat_item,
                    "focus_url": f"{detail_url}?event={repeat_item['id']}",
                    "add_another_url": add_another_url,
                    "forms": forms_with_url,
                }
            )
        return payload

    def _with_verification_focus_urls(self, event_navigation):
        return self._with_readonly_mode_focus_urls(event_navigation, mode="verification")

    def _with_viewonly_focus_urls(self, event_navigation):
        return self._with_readonly_mode_focus_urls(event_navigation, mode="viewonly")

    def _with_readonly_mode_focus_urls(self, event_navigation, *, mode: str):
        detail_url = reverse(
            "subject:subject_detail",
            kwargs={
                "study_id": self.get_study_id(),
                "subject_id": self.object.pk,
            },
        )
        payload = []
        for event_item in event_navigation:
            forms_with_url = [
                {
                    **form_item,
                    "focus_url": (
                        f"{detail_url}?mode={mode}&event={event_item['id']}&form={form_item['id']}"
                    ),
                }
                for form_item in event_item["forms"]
            ]
            payload.append(
                {
                    **event_item,
                    "focus_url": f"{detail_url}?mode={mode}&event={event_item['id']}",
                    "forms": forms_with_url,
                },
            )
        return payload

    def get_crf_context_adapter(self):
        if not hasattr(self, "_crf_context_adapter"):
            self._crf_context_adapter = self.crf_context_adapter_class()
        return self._crf_context_adapter
