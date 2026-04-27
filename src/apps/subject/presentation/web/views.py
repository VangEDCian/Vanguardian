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
        "text": "text",
        "entry_box": "text",
        "entry box": "text",
        "textbox": "text",
        "text box": "text",
        "textarea": "textarea",
        "text_area": "textarea",
        "text area": "textarea",
        "number": "number",
        "numeric": "number",
        "select": "select",
        "dropdown": "select",
        "dropdown list": "select",
        "radio": "radio",
        "radio_button_list": "radio",
        "radio button list": "radio",
        "checkbox": "checkbox",
        "checkbox_list": "multi_select",
        "checkbox list": "multi_select",
        "multi_select": "multi_select",
        "multi select": "multi_select",
        "date": "date",
        "date_picker": "date",
        "date picker": "date",
        "datetime": "datetime",
        "time_picker": "datetime",
        "time picker": "datetime",
        "time": "datetime",
        "label_only": "label_only",
        "label only": "label_only",
        "calculated_field": "label_only",
        "calculated field": "label_only",
        "calculated": "label_only",
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
            return "text"
        normalized_value = str(raw_control_type).strip().lower()
        return cls.supported_control_type_map.get(normalized_value, "unsupported")

    @staticmethod
    def _normalize_control_layout(raw_control_layout):
        normalized_value = str(raw_control_layout or "").strip().lower()
        if normalized_value in {"normal", "card", "table_row"}:
            return normalized_value
        return "normal"

    @staticmethod
    def _normalize_section_layout_type(raw_layout_type):
        normalized_value = str(raw_layout_type or "").strip().lower()
        if normalized_value in {"section", "table"}:
            return normalized_value
        return "section"

    @staticmethod
    def _normalize_schema_boolean(raw_value, *, default):
        if raw_value is None:
            return default
        if isinstance(raw_value, bool):
            return raw_value
        normalized_value = str(raw_value).strip().lower()
        if normalized_value in {"1", "true", "yes", "on"}:
            return True
        if normalized_value in {"0", "false", "no", "off"}:
            return False
        return default

    @classmethod
    def _default_table_layout_schema(cls):
        return {
            "show_table_header": True,
            "response_direction": "horizontal",
            "columns": [
                {
                    "key": "index",
                    "label": "#",
                    "width": "40px",
                    "source": "display_order",
                    "header_class": "subject-form-table-section__head--index",
                    "cell_class": "subject-form-table-row__cell--index",
                },
                {
                    "key": "criterion",
                    "label": _("Criterion"),
                    "width": "",
                    "source": "label",
                    "header_class": "subject-form-table-section__head--criterion",
                    "cell_class": "subject-form-table-row__cell--criterion",
                },
                {
                    "key": "response",
                    "label": _("Response"),
                    "width": "239px",
                    "source": "control",
                    "header_class": "subject-form-table-section__head--response",
                    "cell_class": "subject-form-table-row__cell--response",
                },
            ],
        }

    @classmethod
    def _normalize_table_column_schema(cls, raw_column):
        if not isinstance(raw_column, dict):
            return None

        source = str(raw_column.get("source") or raw_column.get("key") or "").strip().lower()
        source_aliases = {
            "ordinal": "display_order",
            "index": "display_order",
            "#": "display_order",
            "criterion": "label",
            "response": "control",
        }
        normalized_source = source_aliases.get(source, source)
        if normalized_source not in {"display_order", "label", "control", "field_key", "data_type"}:
            return None

        default_schema = {
            "display_order": {
                "key": "index",
                "label": "#",
                "cell_class": "subject-form-table-row__cell--index",
                "header_class": "subject-form-table-section__head--index",
            },
            "label": {
                "key": "criterion",
                "label": _("Criterion"),
                "cell_class": "subject-form-table-row__cell--criterion",
                "header_class": "subject-form-table-section__head--criterion",
            },
            "control": {
                "key": "response",
                "label": _("Response"),
                "cell_class": "subject-form-table-row__cell--response",
                "header_class": "subject-form-table-section__head--response",
            },
            "field_key": {
                "key": "field_key",
                "label": _("Field Key"),
                "cell_class": "subject-form-table-row__cell--field-key",
                "header_class": "subject-form-table-section__head--field-key",
            },
            "data_type": {
                "key": "data_type",
                "label": _("Data Type"),
                "cell_class": "subject-form-table-row__cell--data-type",
                "header_class": "subject-form-table-section__head--data-type",
            },
        }[normalized_source]

        return {
            "key": str(raw_column.get("key") or default_schema["key"]).strip() or default_schema["key"],
            "label": raw_column.get("label") or default_schema["label"],
            "width": str(raw_column.get("width") or "").strip(),
            "source": normalized_source,
            "header_class": (
                str(raw_column.get("header_class") or default_schema["header_class"]).strip()
            ),
            "cell_class": (
                str(raw_column.get("cell_class") or default_schema["cell_class"]).strip()
            ),
        }

    @classmethod
    def _normalize_table_layout_schema(cls, raw_schema):
        default_schema = cls._default_table_layout_schema()
        if not isinstance(raw_schema, dict):
            return default_schema

        raw_columns = raw_schema.get("columns")
        normalized_columns = []
        if isinstance(raw_columns, list):
            for raw_column in raw_columns:
                normalized_column = cls._normalize_table_column_schema(raw_column)
                if normalized_column is not None:
                    normalized_columns.append(normalized_column)
        if not normalized_columns:
            normalized_columns = default_schema["columns"]

        response_direction = str(raw_schema.get("response_direction") or "").strip().lower()
        if response_direction not in {"horizontal", "vertical"}:
            response_direction = default_schema["response_direction"]

        return {
            "show_table_header": cls._normalize_schema_boolean(
                raw_schema.get("show_table_header"),
                default=default_schema["show_table_header"],
            ),
            "response_direction": response_direction,
            "columns": normalized_columns,
        }

    @classmethod
    def _build_table_row_cells(cls, field, columns):
        row_cells = []
        for column in columns:
            source = column.get("source")
            cell_payload = {
                "key": column.get("key"),
                "source": source,
                "cell_class": column.get("cell_class") or "",
            }
            if source == "control":
                row_cells.append(
                    {
                        **cell_payload,
                        "kind": "control",
                    }
                )
                continue

            if source == "display_order":
                value = field.get("display_order")
            elif source == "label":
                value = field.get("label") or field.get("field_key")
            elif source == "field_key":
                value = field.get("field_key")
            elif source == "data_type":
                value = field.get("data_type")
            else:
                value = field.get(source)

            row_cells.append(
                {
                    **cell_payload,
                    "kind": "text",
                    "text": value if value not in (None, "") else "—",
                    "show_required": source == "label" and field.get("is_required"),
                    "helper_text": field.get("helper_text") if source == "label" else "",
                }
            )

        return row_cells

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
            section_layout_config = section_template.get("layout_config") or {}
            section_layout_type = self._normalize_section_layout_type(
                section_layout_config.get("layout_type")
            )
            table_layout = self._normalize_table_layout_schema(
                section_layout_config.get("custom_layout_schema")
            )

            section_key = (
                section_template.get("id")
                or section_template.get("code")
                or f"general::{section_title}"
            )
            if section_key not in sections_by_key:
                sections_by_key[section_key] = {
                    "id": section_template.get("id"),
                    "code": section_template.get("code"),
                    "code_class": str(section_template.get("code") or "").strip().lower(),
                    "title": section_title,
                    "order": section_order,
                    "layout_type": section_layout_type,
                    "layout_schema": section_layout_config.get("custom_layout_schema") or {},
                    "table_layout": table_layout,
                    "layout_css_class": (
                        section_layout_config.get("custom_css_class") or ""
                    ).strip(),
                    "show_section_header": section_layout_config.get(
                        "show_section_header", True
                    ),
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
            if section.get("layout_type") == "table":
                section["table_layout"] = self._normalize_table_layout_schema(
                    section.get("layout_schema")
                )
                section["fields"] = [
                    {
                        **field,
                        "table_row_cells": self._build_table_row_cells(
                            field,
                            section["table_layout"]["columns"],
                        ),
                    }
                    for field in section["fields"]
                ]
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
