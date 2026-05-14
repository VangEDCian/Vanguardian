import json

from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView

from apps.core.choices import DataCapturePageEntryStatusChoices, DataCapturePageStateStatusChoices
from apps.datacapture.public import (
    ensure_draft_page_state_if_not_exists,
    get_latest_page_entry_for_subject_visit_crf,
    get_latest_submitted_page_entry_for_subject_visit_crf,
    get_page_state_id_for_subject_visit_crf,
    get_page_state_status_for_subject_visit_crf,
    get_verified_field_template_ids_for_subject_visit_crf,
)
from apps.shared.views import AuthenticateTemplateContextMixin
from apps.subject.application.services.form_field_review_table import FormFieldReviewTableService
from apps.subject.application.services.form_verification_navigation import (
    SubjectFormVerificationNavigationService,
)
from apps.subject.application.services.subject_list_verify_form_visibility import VERIFY_FORM_PERMISSION
from apps.subject.infrastructure.repositories import DjangoSubjectEventInstanceFileRepository
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
    event_instance_file_repository_class = DjangoSubjectEventInstanceFileRepository

    def get_event_instance_file_repository(self):
        return self.event_instance_file_repository_class()

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

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        mode = (request.GET.get("mode") or "").strip().lower()
        if mode == "verification" and not request.GET.get("event") and not request.GET.get("form"):
            raw_nav = self._build_event_navigation()
            submitted_nav = SubjectFormVerificationNavigationService.filter_submitted_only(
                subject_id=self.object.pk,
                event_navigation=raw_nav,
            )
            first_url = SubjectFormVerificationNavigationService.first_verification_url(
                study_id=self.get_study_id(),
                subject_id=self.object.pk,
                event_navigation_submitted=submitted_nav,
            )
            if first_url:
                return redirect(first_url)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):  # noqa: C901
        context = super().get_context_data(**kwargs)
        subject = self.object
        is_form_verification_mode = (self.request.GET.get("mode") or "").strip().lower() == "verification"

        raw_event_navigation = self._build_event_navigation()
        if is_form_verification_mode:
            submitted_nav = SubjectFormVerificationNavigationService.filter_submitted_only(
                subject_id=subject.pk,
                event_navigation=raw_event_navigation,
            )
            event_navigation = self._with_verification_focus_urls(submitted_nav)
        else:
            event_navigation = self._with_focus_urls(raw_event_navigation)

        focus_event_id = (self.request.GET.get("event") or "").strip()
        focused_event = self._resolve_focus(event_navigation, focus_event_id)
        if focused_event is None and event_navigation:
            focused_event = event_navigation[0]
        focused_forms = focused_event["forms"] if focused_event else []

        focus_form_id = (self.request.GET.get("form") or "").strip()
        focused_form = self._resolve_focus(focused_forms, focus_form_id)
        if focused_form is None and focused_forms:
            focused_form = focused_forms[0]
        focused_form_fields = []
        focused_page_status = ""
        focused_latest_entry = None
        focused_latest_submitted_entry = None
        focused_render_entry = None
        focused_entry_values = {}
        previous_submitted_entry_values = {}
        previous_data_values = None
        current_data_values = {}
        reason_required_field_keys = []
        is_viewing_submitted_version = False
        focus_detail_url = ""
        view_submitted_url = ""
        view_current_url = ""
        datacapture_save_url = ""
        datacapture_submit_url = ""
        datacapture_delete_draft_url = ""
        event_file_import_url = ""
        event_file_preview_url = ""
        has_event_instance_files = False
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
                        if is_form_verification_mode:
                            focus_detail_url = (
                                f"{detail_url}?mode=verification&event={focused_event['id']}&form={form_id}"
                            )
                        else:
                            focus_detail_url = f"{detail_url}?event={focused_event['id']}&form={form_id}"
                    focused_page_status = get_page_state_status_for_subject_visit_crf(
                        subject_id=subject.pk,
                        visit_id=visit_id,
                        crf_template_id=template_id,
                    )
                    if (
                        not focused_page_status
                        and focused_event
                        and not is_form_verification_mode
                        and visit_id is not None
                    ):
                        ensure_draft_page_state_if_not_exists(
                            subject_id=subject.pk,
                            visit_id=visit_id,
                            crf_template_id=template_id,
                            actor_user_id=self.request.user.pk,
                        )
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
                        if is_form_verification_mode:
                            focused_render_entry = focused_latest_submitted_entry
                            if (
                                focused_render_entry is None
                                and focused_latest_entry is not None
                                and focused_latest_entry.status
                                == DataCapturePageEntryStatusChoices.SUBMITTED
                            ):
                                focused_render_entry = focused_latest_entry
                            focused_entry_values = self._extract_entry_payload_map(
                                focused_render_entry.data if focused_render_entry else ""
                            )
                            current_data_values = dict(focused_entry_values)
                            is_viewing_submitted_version = (
                                focused_render_entry is not None
                                and focused_render_entry.status
                                == DataCapturePageEntryStatusChoices.SUBMITTED
                            )
                        else:
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
                            current_data_values = self._extract_entry_payload_map(
                                focused_latest_entry.data if focused_latest_entry else ""
                            )
                            if focused_latest_entry is not None:
                                if focused_latest_entry.status == DataCapturePageEntryStatusChoices.SUBMITTED:
                                    previous_data_values = self._extract_entry_payload_map(
                                        focused_latest_entry.data
                                    )
                                elif (
                                    focused_latest_entry.status == DataCapturePageEntryStatusChoices.DRAFT
                                    and focused_latest_submitted_entry is not None
                                ):
                                    previous_data_values = self._extract_entry_payload_map(
                                        focused_latest_submitted_entry.data
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
                    verified_field_template_ids = get_verified_field_template_ids_for_subject_visit_crf(
                        subject_id=subject.pk,
                        visit_id=int(focused_event["id"]) if focused_event else None,
                        crf_template_id=template_id,
                    )
                    reason_required_field_keys = []
                    for field in focused_form_fields:
                        try:
                            field_template_id = int(field.get("id"))
                        except (TypeError, ValueError):
                            continue
                        field_key = str(field.get("field_key") or "").strip()
                        if field_template_id in verified_field_template_ids:
                            if field_key:
                                reason_required_field_keys.append(field_key)
                            reason_required_field_keys.append(f"field_{field_template_id}")
                    reason_required_field_keys = sorted(set(reason_required_field_keys))
                    if focused_event and not is_form_verification_mode:
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
                    previous_data_values = None
                    current_data_values = {}
                    reason_required_field_keys = []
                    is_viewing_submitted_version = False
                    focus_detail_url = ""
                    view_submitted_url = ""
                    view_current_url = ""
                    datacapture_save_url = ""
                    datacapture_submit_url = ""
                    datacapture_delete_draft_url = ""

        if focused_event and not is_form_verification_mode:
            try:
                focused_event_id = int(focused_event["id"])
            except (TypeError, ValueError):
                focused_event_id = None
            if focused_event_id is not None:
                event_file_import_url = reverse(
                    "subject:subject_eventinstance_file_import",
                    kwargs={
                        "study_id": self.get_study_id(),
                        "subject_id": subject.pk,
                        "event_instance_id": focused_event_id,
                    },
                )
                event_file_preview_url = reverse(
                    "subject:subject_eventinstance_file_preview",
                    kwargs={
                        "study_id": self.get_study_id(),
                        "subject_id": subject.pk,
                        "event_instance_id": focused_event_id,
                    },
                )
                preview_query_parts = []
                if focused_form:
                    preview_query_parts.append(f"form={focused_form.get('id', '')}")
                if is_viewing_submitted_version:
                    preview_query_parts.append("view=submitted")
                if preview_query_parts:
                    event_file_preview_url = f"{event_file_preview_url}?{'&'.join(preview_query_parts)}"
                has_event_instance_files = self.get_event_instance_file_repository().has_files(
                    event_instance_id=focused_event_id,
                )
        form_render_sections = self._build_form_render_sections(
            focused_form_fields,
            entry_payload_map=focused_entry_values,
        )

        form_verification_review = None
        form_verification_verify_checked_url = ""
        # Do not require non-empty focused_form_fields: the verification endpoint still
        # needs visit + template IDs to initialize field review rows.
        if is_form_verification_mode and focused_form and focused_event:
            try:
                visit_pk = int(focused_event["id"])
                template_pk = int(focused_form.get("form_definition_id") or "")
            except (TypeError, ValueError):
                visit_pk = None
                template_pk = None
            if visit_pk is not None and template_pk is not None:
                page_state_pk = get_page_state_id_for_subject_visit_crf(
                    subject_id=subject.pk,
                    visit_id=visit_pk,
                    crf_template_id=template_pk,
                )
                verified_field_template_ids = get_verified_field_template_ids_for_subject_visit_crf(
                    subject_id=subject.pk,
                    visit_id=visit_pk,
                    crf_template_id=template_pk,
                )
                form_verification_review = FormFieldReviewTableService().build_for_verification(
                    subject_code=subject.subject_code or subject.screening_code or "",
                    site_id=subject.site.code,
                    event_name=str(focused_event.get("name") or ""),
                    event_instance_id=visit_pk,
                    form_name=str(focused_form.get("title") or ""),
                    form_status=focused_page_status,
                    entry_version=str(getattr(focused_render_entry, "entry_version", "") or ""),
                    entry_updated_at=getattr(focused_render_entry, "updated_at", None),
                    entry_updated_by_id=getattr(focused_render_entry, "updated_by_id", None),
                    field_templates_payload=focused_form_fields,
                    entry_payload=focused_entry_values,
                    page_state_id=page_state_pk,
                    verified_field_template_ids=verified_field_template_ids,
                )
                if self.request.user.has_perm(VERIFY_FORM_PERMISSION):
                    if (focused_page_status or "").strip().lower() in {
                        DataCapturePageStateStatusChoices.SUBMITTED.value,
                        DataCapturePageStateStatusChoices.UNDER_REVIEW.value,
                    }:
                        form_verification_verify_checked_url = reverse(
                            "subject:subject_form_verification_verify_checked",
                            kwargs={
                                "study_id": self.get_study_id(),
                                "subject_id": subject.pk,
                                "visit_id": visit_pk,
                                "crf_template_id": template_pk,
                            },
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
        context["previous_data_values"] = previous_data_values
        context["current_data_values"] = current_data_values
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
        context["reason_required_field_keys"] = reason_required_field_keys
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
        context["event_file_import_url"] = event_file_import_url
        context["event_file_preview_url"] = event_file_preview_url
        context["has_event_instance_files"] = has_event_instance_files
        context["is_form_verification_mode"] = is_form_verification_mode
        context["form_verification_review"] = form_verification_review
        context["form_verification_verify_checked_url"] = form_verification_verify_checked_url
        context["form_verification_fields_locked"] = (
            is_form_verification_mode
            and (focused_page_status or "").strip().lower()
            in {
                DataCapturePageStateStatusChoices.VERIFIED.value,
                DataCapturePageStateStatusChoices.LOCKED.value,
                DataCapturePageStateStatusChoices.FINALIZED.value,
            }
        )
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
