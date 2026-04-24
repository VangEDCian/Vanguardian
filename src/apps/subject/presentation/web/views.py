import json
import re

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, ListView
from django_filters.views import FilterView
from django_tables2 import SingleTableMixin

from apps.crf.public import CrfContextAdapter
from apps.shared.context_processors import StudyDropdownHandler, SiteDropdownHandler
from apps.shared.views import AuthenticateTemplateContextMixin
from apps.core.choices.study import EventInstanceStatusChoices
from apps.study.application.queries.site_directory import StudySiteDirectoryQueryService
from apps.study.models import EventFormBinding
from apps.study.presentation.web.viewpackages._helpers import _user_has_study_access
from apps.subject.application.commands.create_subject import (
    CreateSubjectCommand,
    CreateSubjectService,
)
from apps.subject.models import Subject, SubjectEventInstance
from apps.subject.presentation.web.formpackages import SubjectsToolbarForm
from apps.subject.presentation.web.tables import SubjectListTable

__all__ = ["SubjectListView", "SubjectDetailView", "SubjectCreateView"]


class SubjectAbstractVerifyStudy(View):
    study_obj = None

    def get_study_id(self):
        return self.kwargs["study_id"]

    def dispatch(self, request, *args, **kwargs):
        study_id = self.get_study_id()
        self.study_obj = StudySiteDirectoryQueryService.get_study_id(study_id=study_id)
        if self.study_obj:
            if not _user_has_study_access(request.user, study_id):
                raise PermissionDenied
            return super().dispatch(request, *args, **kwargs)
        raise Http404


class SubjectListView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuthenticateTemplateContextMixin,
    SingleTableMixin,
    FilterView,
    ListView,
    SubjectAbstractVerifyStudy,
):
    permission_required = "subject.view_subject_list"
    raise_exception = True
    layout_nav_key = "SUBJECTS"
    layout_breadcrumb_label = _("SUBJECTS")

    model = Subject
    template_name = "subject/subjects.html"
    table_class = SubjectListTable
    filterset_class = SubjectsToolbarForm
    paginate_by = 25

    @staticmethod
    def _get_resolved_study_id(request):
        return StudyDropdownHandler(request=request).build().selected_id

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(study_id=self.get_study_id(), deleted=False)
            .select_related("site", "study", "enrollment", "randomization")
            .order_by("current_sequence", "id")
        )

    def get(self, request, *args, **kwargs):
        path_study_id = self.get_study_id()
        resolved_study_id = self._get_resolved_study_id(request)
        if path_study_id and resolved_study_id:
            if path_study_id == resolved_study_id:
                return super().get(request, *args, **kwargs)
            return redirect(
                reverse(
                    "subject:subject_list",
                    kwargs={"study_id": resolved_study_id},
                )
            )
        return redirect(reverse("dashboard:main"))


class SubjectDetailView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuthenticateTemplateContextMixin,
    DetailView,
    SubjectAbstractVerifyStudy,
):
    permission_required = "subject.view_subject_detail"
    raise_exception = True
    layout_nav_key = "SUBJECTS"
    template_name = "subject/subject_detail.html"

    model = Subject
    pk_url_kwarg = "subject_id"
    crf_context_adapter_class = CrfContextAdapter
    supported_control_type_map = {
        "checkbox list": "checkbox_list",
        "checkbox": "checkbox_list",
        "radio button list": "radio_button_list",
        "radio": "radio_button_list",
        "dropdown list": "dropdown",
        "dropdown": "dropdown",
        "select": "dropdown",
        "date picker": "date_picker",
        "date": "date_picker",
        "time picker": "time_picker",
        "time": "time_picker",
        "entry box": "entry_box",
        "textbox": "entry_box",
        "text box": "entry_box",
        "text area": "text_area",
        "textarea": "text_area",
        "calculated field": "calculated_field",
        "calculated": "calculated_field",
    }

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(study_id=self.get_study_id(), deleted=False)
            .select_related("site", "study")
        )

    def get_layout_show_breadcrumb_trail(self):
        return False

    def get_layout_breadcrumb_label(self):
        subject = getattr(self, "object", None)
        if subject is None:
            return super().get_layout_breadcrumb_label()
        return subject.subject_code or subject.screening_code or _("SUBJECT DETAIL")

    def get_layout_detail_meta_items(self):
        subject = getattr(self, "object", None)
        if subject is None:
            return super().get_layout_detail_meta_items()

        return (
            {
                "label": _("Site"),
                "value": subject.site.code,
            },
            {
                "label": _("Subject ID"),
                "value": subject.subject_code or subject.screening_code or "—",
            },
            {
                "label": _("Study"),
                "value": subject.study.code,
            },
        )

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
                template_name = template.safe_translation_getter(
                    "name",
                    default=template.code,
                    any_language=True,
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

    def get_crf_context_adapter(self):
        if not hasattr(self, "_crf_context_adapter"):
            self._crf_context_adapter = self.crf_context_adapter_class()
        return self._crf_context_adapter

    @classmethod
    def _normalize_control_type(cls, raw_control_type):
        if not raw_control_type:
            return "entry_box"
        normalized_value = str(raw_control_type).strip().lower()
        return cls.supported_control_type_map.get(normalized_value, "unsupported")

    @staticmethod
    def _normalize_control_layout(raw_control_layout):
        normalized_value = str(raw_control_layout or "").strip().lower()
        if normalized_value in {"normal", "card", "table_row"}:
            return normalized_value
        return "normal"

    @staticmethod
    def _parse_choice_options(raw_value):
        if not raw_value:
            return []

        if isinstance(raw_value, list):
            normalized_options = SubjectDetailView._normalize_choice_option_items(raw_value)
            if normalized_options:
                return normalized_options

        if isinstance(raw_value, str):
            stripped_value = raw_value.strip()
            if stripped_value.startswith("[") and stripped_value.endswith("]"):
                try:
                    loaded_options = json.loads(stripped_value)
                except json.JSONDecodeError:
                    loaded_options = None
                else:
                    normalized_options = SubjectDetailView._normalize_choice_option_items(
                        loaded_options
                    )
                    if normalized_options:
                        return normalized_options

        normalized = str(raw_value).replace("\r", "\n")
        normalized = normalized.replace("|", "\n").replace(";", "\n")
        lines = [line.strip() for line in normalized.split("\n") if line.strip()]
        options = []

        pair_pattern = re.compile(
            r"([^=]+?)\s*=\s*([^=]+?)(?=\s+[^=]+?\s*=|$)"
        )
        for line in lines:
            if "=" in line:
                matched_pairs = pair_pattern.findall(line)
                if matched_pairs:
                    for label, value in matched_pairs:
                        options.append(
                            {
                                "label": label.strip(),
                                "value": value.strip(),
                            }
                        )
                    continue
                label, value = line.split("=", 1)
                options.append({"label": label.strip(), "value": value.strip()})
                continue

            options.append({"label": line, "value": line})

        return [option for option in options if option["label"]]

    @staticmethod
    def _normalize_choice_option_items(raw_items):
        if not isinstance(raw_items, list):
            return []

        options = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue

            label = str(item.get("label") or "").strip()
            value = str(item.get("value") or "").strip()
            if not label:
                continue
            if not value:
                value = label
            options.append({"value": value, "label": label})

        return options

    def _build_form_render_sections(self, focused_form_fields):
        if not focused_form_fields:
            return []

        sections_by_key = {}
        for field in focused_form_fields:
            section_template = field.get("section_template") or {}
            section_title = (section_template.get("name") or "").strip() or _("General")
            section_order = section_template.get("display_order")
            if section_order is None:
                section_order = 999999

            section_key = (
                section_template.get("id")
                or section_template.get("code")
                or f"general::{section_title}"
            )
            if section_key not in sections_by_key:
                sections_by_key[section_key] = {
                    "title": section_title,
                    "order": section_order,
                    "fields": [],
                    "columns": 1,
                }

            ui_config = field.get("ui_config") or {}
            control_type = self._normalize_control_type(ui_config.get("control_type"))
            control_layout = self._normalize_control_layout(ui_config.get("control_layout"))
            options = self._parse_choice_options(ui_config.get("options") or field.get("codelist"))
            placeholder_text = (ui_config.get("text") or "").strip()
            helper_text = (field.get("comments") or "").strip()

            sections_by_key[section_key]["fields"].append(
                {
                    "id": field.get("id"),
                    "field_key": field.get("field_key"),
                    "label": field.get("label") or field.get("field_key"),
                    "data_type": field.get("data_type"),
                    "display_order": field.get("display_order") or 999999,
                    "control_type": control_type,
                    "control_layout": control_layout,
                    "raw_control_type": ui_config.get("control_type"),
                    "placeholder_text": placeholder_text,
                    "helper_text": helper_text,
                    "options": options,
                    "is_required": "required" in (ui_config.get("behavior") or "").lower(),
                    "classes": (ui_config.get("classes") or "").strip(),
                }
            )

        payload = []
        ordered_sections = sorted(
            sections_by_key.values(),
            key=lambda section: (
                section.get("order", 999999),
                str(section.get("title") or "").lower(),
            ),
        )
        for section in ordered_sections:
            section["fields"] = sorted(
                section["fields"],
                key=lambda field: (
                    field.get("display_order", 999999),
                    str(field.get("label") or "").lower(),
                ),
            )
            field_count = len(section["fields"])
            if field_count <= 1:
                section["columns"] = 1
            elif field_count == 2:
                section["columns"] = 2
            else:
                section["columns"] = 3
            payload.append(section)
        return payload

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subject = self.object
        event_navigation = self._with_focus_urls(self._build_event_navigation())

        focus_event_id = (self.request.GET.get("event") or "").strip()
        focused_event = self._resolve_focus(event_navigation, focus_event_id)
        focused_forms = focused_event["forms"] if focused_event else []

        focus_form_id = (self.request.GET.get("form") or "").strip()
        focused_form = self._resolve_focus(focused_forms, focus_form_id)
        focused_form_fields = []
        if focused_form:
            form_definition_id = focused_form.get("form_definition_id")
            if form_definition_id:
                try:
                    focused_form_fields = self.get_crf_context_adapter().list_template_fields_with_ui_config(
                        template_id=int(form_definition_id),
                    )
                except (TypeError, ValueError):
                    focused_form_fields = []
        form_render_sections = self._build_form_render_sections(focused_form_fields)

        context["back_url"] = reverse(
            "subject:subject_list", kwargs={"study_id": self.get_study_id()},
        )
        context["subject_obj"] = subject
        context["subject_display_id"] = subject.subject_code or subject.screening_code or "—"
        context["event_navigation"] = event_navigation
        context["focused_event"] = focused_event
        context["focused_forms"] = focused_forms
        context["focused_form"] = focused_form
        context["focused_form_fields"] = focused_form_fields
        context["form_render_sections"] = form_render_sections
        context["study_header_label"] = subject.study.name or subject.study.code
        return context


class SubjectCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SubjectAbstractVerifyStudy,
):
    permission_required = "subject.create_subject"
    raise_exception = True

    def post(self, request, *args, **kwargs):
        study_id = self.get_study_id()
        site_id = SiteDropdownHandler(
            request=request,
            study_id=study_id,
        ).build().selected_id
        if site_id is None:
            raise Http404

        subject = CreateSubjectService().execute(
            CreateSubjectCommand(
                study_id=study_id,
                site_id=site_id,
                actor_user_id=request.user.pk,
            ),
        )
        return redirect(
            reverse(
                "subject:subject_detail",
                kwargs={"study_id": study_id, "subject_id": subject.pk},
            ),
        )
