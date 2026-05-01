from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView

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
