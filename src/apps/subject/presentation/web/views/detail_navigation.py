from django.urls import reverse
from django.utils.translation import get_language

from apps.core.choices.study import EventInstanceStatusChoices
from apps.crf.application.services.crf_template_query import CrfTemplateQueryService
from apps.crf.public import CrfContextAdapter
from apps.study.models import EventFormBinding
from apps.subject.models import SubjectEventInstance


class SubjectDetailNavigationMixin:
    crf_context_adapter_class = CrfContextAdapter

    def _build_event_navigation(self):
        event_instances = list(
            SubjectEventInstance.objects.filter(
                subject_id=self.object.pk,
                deleted=False,
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

        payload = []
        for event_instance in event_instances:
            forms = []
            for binding in bindings_map.get(event_instance.event_definition_id, []):
                template = binding.form_definition
                lang = CrfTemplateQueryService._normalize_language_code(get_language())
                template_name = CrfTemplateQueryService._translated_value(
                    template,
                    lang,
                    "name",
                    default=template.code,
                )
                forms.append(
                    {
                        "id": str(binding.pk),
                        "form_definition_id": str(template.pk),
                        "title": template_name,
                        "code": template.code,
                    }
                )

            payload.append(
                {
                    "id": str(event_instance.pk),
                    "code": event_instance.event_code_snapshot or event_instance.event_definition.code,
                    "name": event_instance.event_name_snapshot or event_instance.event_definition.name,
                    "status": event_instance.status,
                    "forms": forms,
                }
            )
        return payload

    @staticmethod
    def _resolve_focus(items, focus_id):
        if not items:
            return None
        for item in items:
            if item["id"] == focus_id:
                return item
        return items[0]

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
                    "forms": forms_with_url,
                },
            )
        return payload

    def _with_verification_focus_urls(self, event_navigation):
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
                        f"{detail_url}?mode=verification&event={event_item['id']}&form={form_item['id']}"
                    ),
                }
                for form_item in event_item["forms"]
            ]
            payload.append(
                {
                    **event_item,
                    "focus_url": f"{detail_url}?mode=verification&event={event_item['id']}",
                    "forms": forms_with_url,
                },
            )
        return payload

    def get_crf_context_adapter(self):
        if not hasattr(self, "_crf_context_adapter"):
            self._crf_context_adapter = self.crf_context_adapter_class()
        return self._crf_context_adapter
