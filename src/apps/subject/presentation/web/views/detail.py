import json

from django.urls import reverse
from django.utils.translation import activate
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView

from apps.core.choices import DataCapturePageEntryStatusChoices
from apps.datacapture.public import (
    get_latest_page_entry_for_subject_visit_crf,
    get_latest_submitted_page_entry_for_subject_visit_crf,
    get_page_state_status_for_subject_visit_crf,
)
from apps.shared.views import AuthenticateTemplateContextMixin
from apps.subject.models import Subject
from apps.subject.presentation.web.views.base import SubjectAbstractVerifyStudy
from apps.subject.presentation.web.views.detail_navigation import SubjectDetailNavigationMixin
from apps.subject.presentation.web.views.detail_rendering import SubjectDetailRenderingMixin


class SubjectDetailView(
    SubjectDetailNavigationMixin,
    SubjectDetailRenderingMixin,
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

    def dispatch(self, request, *args, **kwargs):
        # Force English on subject detail to keep CRF UI consistent for testing.
        activate("en")
        request.LANGUAGE_CODE = "en"
        return super().dispatch(request, *args, **kwargs)

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

    def get_context_data(self, **kwargs):  # noqa: C901
        context = super().get_context_data(**kwargs)
        subject = self.object
        event_navigation = self._with_focus_urls(self._build_event_navigation())

        focus_event_id = (self.request.GET.get("event") or "").strip()
        focused_event = self._resolve_focus(event_navigation, focus_event_id)
        focused_forms = focused_event["forms"] if focused_event else []

        focus_form_id = (self.request.GET.get("form") or "").strip()
        focused_form = self._resolve_focus(focused_forms, focus_form_id)
        focused_form_fields = []
        focused_page_status = ""
        focused_latest_entry = None
        focused_latest_submitted_entry = None
        focused_render_entry = None
        focused_entry_values = {}
        previous_submitted_entry_values = {}
        is_viewing_submitted_version = False
        focus_detail_url = ""
        view_submitted_url = ""
        view_current_url = ""
        datacapture_save_url = ""
        datacapture_submit_url = ""
        datacapture_delete_draft_url = ""
        if focused_form:
            form_definition_id = focused_form.get("form_definition_id")
            if form_definition_id:
                try:
                    template_id = int(form_definition_id)
                    visit_id = int(focused_event["id"]) if focused_event else None
                    detail_url = reverse(
                        "subject:subject_detail",
                        kwargs={"study_id": self.get_study_id(), "subject_id": subject.pk},
                    )
                    if focused_event:
                        form_id = focused_form.get("id", "")
                        focus_detail_url = f"{detail_url}?event={focused_event['id']}&form={form_id}"
                    focused_page_status = get_page_state_status_for_subject_visit_crf(
                        subject_id=subject.pk,
                        visit_id=visit_id,
                        crf_template_id=template_id,
                    )
                    if focused_event:
                        focused_latest_entry = get_latest_page_entry_for_subject_visit_crf(
                            subject_id=subject.pk,
                            visit_id=visit_id,
                            crf_template_id=template_id,
                        )
                        focused_latest_submitted_entry = (
                            get_latest_submitted_page_entry_for_subject_visit_crf(
                                subject_id=subject.pk,
                                visit_id=visit_id,
                                crf_template_id=template_id,
                            )
                        )
                        requested_view = (self.request.GET.get("view") or "").strip().lower()
                        focused_render_entry = focused_latest_entry
                        if (
                            requested_view == "submitted"
                            and focused_latest_submitted_entry is not None
                            and focused_latest_entry is not None
                            and focused_latest_submitted_entry.id != focused_latest_entry.id
                        ):
                            focused_render_entry = focused_latest_submitted_entry
                            is_viewing_submitted_version = True
                        focused_entry_values = self._extract_entry_payload_map(
                            focused_render_entry.data if focused_render_entry else ""
                        )
                        if (
                            focused_latest_submitted_entry is not None
                            and focused_latest_entry is not None
                            and focused_latest_submitted_entry.id != focused_latest_entry.id
                        ):
                            previous_submitted_entry_values = self._extract_entry_payload_map(
                                focused_latest_submitted_entry.data
                            )
                        if (
                            focus_detail_url
                            and focused_latest_submitted_entry is not None
                            and focused_latest_entry is not None
                            and focused_latest_submitted_entry.id != focused_latest_entry.id
                        ):
                            view_submitted_url = f"{focus_detail_url}&view=submitted"
                            view_current_url = focus_detail_url
                    focused_form_fields = self.get_crf_context_adapter().list_template_fields_with_ui_config(
                        template_id=template_id,
                    )
                    if focused_event:
                        url_kw = {
                            "study_id": self.get_study_id(),
                            "subject_id": subject.pk,
                            "visit_id": int(focused_event["id"]),
                            "crf_template_id": template_id,
                        }
                        datacapture_save_url = reverse("datacapture:page_save", kwargs=url_kw)
                        datacapture_submit_url = reverse("datacapture:page_submit", kwargs=url_kw)
                        datacapture_delete_draft_url = reverse("datacapture:page_delete_draft", kwargs=url_kw)
                except (TypeError, ValueError):
                    focused_form_fields = []
                    focused_page_status = ""
                    focused_latest_entry = None
                    focused_latest_submitted_entry = None
                    focused_render_entry = None
                    focused_entry_values = {}
                    previous_submitted_entry_values = {}
                    is_viewing_submitted_version = False
                    focus_detail_url = ""
                    view_submitted_url = ""
                    view_current_url = ""
                    datacapture_save_url = ""
                    datacapture_submit_url = ""
                    datacapture_delete_draft_url = ""
        form_render_sections = self._build_form_render_sections(
            focused_form_fields,
            entry_payload_map=focused_entry_values,
        )

        context["back_url"] = reverse(
            "subject:subject_list", kwargs={"study_id": self.get_study_id()},
        )
        context["subject_obj"] = subject
        context["subject_display_id"] = subject.subject_code or subject.screening_code or "—"
        context["event_navigation"] = event_navigation
        context["focused_event"] = focused_event
        context["focused_forms"] = focused_forms
        context["focused_form"] = focused_form
        context["focused_page_status"] = focused_page_status
        context["focused_form_fields"] = focused_form_fields
        context["form_render_sections"] = form_render_sections
        context["focused_latest_entry"] = focused_latest_entry
        context["focused_latest_submitted_entry"] = focused_latest_submitted_entry
        context["focused_render_entry"] = focused_render_entry
        context["previous_submitted_entry_values"] = previous_submitted_entry_values
        context["has_previous_submitted_version"] = (
            focused_latest_submitted_entry is not None
            and focused_render_entry is not None
            and focused_render_entry.status != DataCapturePageEntryStatusChoices.SUBMITTED
            and not is_viewing_submitted_version
        )
        context["is_viewing_submitted_version"] = is_viewing_submitted_version
        context["focus_detail_url"] = focus_detail_url
        context["view_submitted_url"] = view_submitted_url
        context["view_current_url"] = view_current_url
        context["has_submitted_record"] = focused_latest_submitted_entry is not None
        context["can_delete_current_draft"] = (
            focused_latest_entry is not None
            and focused_latest_entry.status == DataCapturePageEntryStatusChoices.DRAFT
            and not is_viewing_submitted_version
            and bool(datacapture_delete_draft_url)
        )
        context["is_focused_render_draft_version"] = (
            focused_render_entry is not None
            and focused_render_entry.status == DataCapturePageEntryStatusChoices.DRAFT
        )
        context["study_header_label"] = subject.study.name or subject.study.code
        context["datacapture_save_url"] = datacapture_save_url
        context["datacapture_submit_url"] = datacapture_submit_url
        context["datacapture_delete_draft_url"] = datacapture_delete_draft_url
        if datacapture_save_url:
            context["datacapture_save_confirm_message"] = _(
                "This page was already submitted. Saving will create a correction version. Continue?"
            )
            context["datacapture_delete_draft_confirm_message"] = _(
                "Delete current draft version? This action marks it as canceled."
            )
        return context

    @staticmethod
    def _extract_entry_payload_map(raw_payload):
        if not raw_payload:
            return {}
        try:
            loaded = json.loads(raw_payload)
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        if not isinstance(loaded, dict):
            return {}
        return loaded
