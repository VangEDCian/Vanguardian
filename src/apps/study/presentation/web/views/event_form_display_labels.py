from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from apps.audit.public import build_audit_request_context
from apps.crf.public import CrfContextAdapter
from apps.shared.views import AuthenticateTemplateContextMixin
from apps.study.application.services import StudyDirectoryQueryService
from apps.study.application.services.event_form_display_label import (
    EventFormDisplayLabelService,
    EventFormDisplayLabelValidationError,
    serialize_event_form_display_errors,
)
from apps.study.presentation.web.forms import EventFormDisplayLabelConfigForm
from apps.study.presentation.web.views.helpers import _user_has_study_access


class StudyEventFormDisplayLabelConfigView(AuthenticateTemplateContextMixin, TemplateView):
    permission_required = "study.create_study_eventdefinition"
    authorization_scope = "STUDY"
    raise_exception = True
    template_name = "study/event_form_display_labels.html"
    layout_nav_key = "STUDIES"

    service_class = EventFormDisplayLabelService
    study_directory_query_service_class = StudyDirectoryQueryService
    crf_context_adapter_class = CrfContextAdapter
    _study = None

    def get_service(self):
        return self.service_class()

    def get_study_directory_query_service(self):
        return self.study_directory_query_service_class()

    def get_crf_context_adapter(self):
        return self.crf_context_adapter_class()

    def dispatch(self, request, *args, **kwargs):
        unauthenticated_response = self.dispatch_authenticated(request)
        if unauthenticated_response is not None:
            return unauthenticated_response
        self._study = self.get_study_directory_query_service().get_study_id(kwargs["study_id"])
        if self._study is None:
            raise Http404
        if not _user_has_study_access(request.user, kwargs["study_id"]):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        binding_rows = self.get_service().list_binding_choices(study_id=self._study.pk)
        selected_binding_id = self._selected_binding_id()
        binding_choice_tuples = [
            (
                str(row["binding_id"]),
                f'{row["event_code"]} / {row["form_code"]} - {row["form_name_en"]}',
            )
            for row in binding_rows
        ]
        context["detail_study"] = self._study
        context["binding_rows"] = binding_rows
        context["selected_binding_id"] = selected_binding_id
        context["token_help"] = ("{{form_name}}", "{{form_code}}", "{{repeat_index}}", "{{field:FIELD_KEY}}")
        context["preview_result"] = kwargs.get("preview_result")
        context["field_choices"] = self._field_choices(selected_binding_id=selected_binding_id)
        context.setdefault(
            "config_form",
            self._build_form(
                selected_binding_id=selected_binding_id,
                binding_choice_tuples=binding_choice_tuples,
            ),
        )
        return context

    def post(self, request, *args, **kwargs):
        selected_binding_id = self._selected_binding_id(from_post=True)
        binding_choice_tuples = [
            (
                str(row["binding_id"]),
                f'{row["event_code"]} / {row["form_code"]} - {row["form_name_en"]}',
            )
            for row in self.get_config_reader().list_binding_choices(study_id=self._study.pk)
        ]
        form = self._build_form(
            selected_binding_id=selected_binding_id,
            binding_choice_tuples=binding_choice_tuples,
            data=request.POST,
        )
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(config_form=form))
        action = (request.POST.get("_action") or "preview").strip().lower()
        if action == "save":
            return self._save(request=request, form=form)
        return self._preview(form=form)

    def _preview(self, *, form):
        preview_result = {
            "vi": self.get_service().preview(
                binding_id=int(form.cleaned_data["event_form_binding_id"]),
                language_code="vi",
                label_template=form.cleaned_data["label_template_vi"],
                fallback_template=form.cleaned_data["fallback_template_vi"],
                empty_value_text=form.cleaned_data["empty_value_text_vi"],
                empty_value_policy=form.cleaned_data["empty_value_policy"],
                max_length=form.cleaned_data["max_length"],
                repeat_index=form.cleaned_data["sample_repeat_index"],
                field_values=form.cleaned_data["sample_field_values"],
            ),
            "en": self.get_service().preview(
                binding_id=int(form.cleaned_data["event_form_binding_id"]),
                language_code="en",
                label_template=form.cleaned_data["label_template_en"],
                fallback_template=form.cleaned_data["fallback_template_en"],
                empty_value_text=form.cleaned_data["empty_value_text_en"],
                empty_value_policy=form.cleaned_data["empty_value_policy"],
                max_length=form.cleaned_data["max_length"],
                repeat_index=form.cleaned_data["sample_repeat_index"],
                field_values=form.cleaned_data["sample_field_values"],
            ),
        }
        return self.render_to_response(
            self.get_context_data(
                config_form=form,
                preview_result=preview_result,
            )
        )

    def _save(self, *, request, form):
        try:
            self.get_service().save_config(
                binding_id=int(form.cleaned_data["event_form_binding_id"]),
                actor_user_id=request.user.pk,
                is_enabled=form.cleaned_data["is_enabled"],
                max_length=form.cleaned_data["max_length"],
                use_choice_display_label=form.cleaned_data["use_choice_display_label"],
                empty_value_policy=form.cleaned_data["empty_value_policy"],
                translations={
                    "vi": {
                        "label_template": form.cleaned_data["label_template_vi"],
                        "fallback_template": form.cleaned_data["fallback_template_vi"],
                        "empty_value_text": form.cleaned_data["empty_value_text_vi"],
                    },
                    "en": {
                        "label_template": form.cleaned_data["label_template_en"],
                        "fallback_template": form.cleaned_data["fallback_template_en"],
                        "empty_value_text": form.cleaned_data["empty_value_text_en"],
                    },
                },
                **build_audit_request_context(request),
            )
        except EventFormDisplayLabelValidationError as exc:
            for error in serialize_event_form_display_errors(exc):
                form.add_error(None, error["message"])
            return self.render_to_response(self.get_context_data(config_form=form))
        messages.success(request, _("Event form display label configuration saved."))
        return redirect(
            f'{reverse("study:study_event_form_display_labels", kwargs={"study_id": self._study.pk})}'
            f'?binding_id={form.cleaned_data["event_form_binding_id"]}'
        )

    def _selected_binding_id(self, *, from_post=False):
        source = self.request.POST if from_post else self.request.GET
        raw_value = (source.get("binding_id") or source.get("event_form_binding_id") or "").strip()
        if not raw_value:
            return None
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return None

    def _build_form(self, *, selected_binding_id, binding_choice_tuples, data=None):
        initial = {}
        if selected_binding_id is not None and data is None:
            snapshot = self.get_service().get_config(binding_id=selected_binding_id)
            if snapshot is not None:
                initial = {
                    "event_form_binding_id": str(snapshot.binding_id),
                    "is_enabled": snapshot.is_enabled,
                    "max_length": snapshot.max_length,
                    "use_choice_display_label": snapshot.use_choice_display_label,
                    "empty_value_policy": snapshot.empty_value_policy,
                    "label_template_vi": snapshot.translations.get("vi").label_template if snapshot.translations.get("vi") else "",
                    "fallback_template_vi": snapshot.translations.get("vi").fallback_template if snapshot.translations.get("vi") else "",
                    "empty_value_text_vi": snapshot.translations.get("vi").empty_value_text if snapshot.translations.get("vi") else "",
                    "label_template_en": snapshot.translations.get("en").label_template if snapshot.translations.get("en") else "",
                    "fallback_template_en": snapshot.translations.get("en").fallback_template if snapshot.translations.get("en") else "",
                    "empty_value_text_en": snapshot.translations.get("en").empty_value_text if snapshot.translations.get("en") else "",
                }
            else:
                initial = {
                    "event_form_binding_id": str(selected_binding_id),
                    "is_enabled": True,
                    "use_choice_display_label": True,
                    "empty_value_policy": "FALLBACK",
                    "max_length": 120,
                }
        return EventFormDisplayLabelConfigForm(
            data=data,
            initial=initial,
            binding_choices=binding_choice_tuples,
        )

    def _field_choices(self, *, selected_binding_id):
        if selected_binding_id is None:
            return []
        binding = self.get_service().get_binding_snapshot(binding_id=selected_binding_id)
        template_id = binding["form_definition_id"] if binding is not None else None
        if template_id is None:
            return []
        return self.get_crf_context_adapter().list_template_field_schema_for_display_label(
            template_id=template_id,
        )


__all__ = ["StudyEventFormDisplayLabelConfigView"]
