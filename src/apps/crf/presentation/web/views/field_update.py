import json

from django.db import IntegrityError
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse

from apps.audit.public import build_audit_request_context
from apps.crf.application.form_builder_orchestration import (
    FormBuilderOrchestrationService,
    StudyScopeViolationError,
)
from apps.crf.application.form_builder_queries import FormBuilderReadModelService
from apps.crf.domain.exceptions import FormBuilderDomainValidationError
from apps.crf.presentation.web.forms import CrfFieldUpdateForm
from apps.crf.presentation.web.mappers.form_builder_commands import to_update_field_aggregate_command
from apps.crf.presentation.web.views.builder import CrfFormBuilderView
from apps.shared.context_processors import StudyDropdownHandler
from apps.shared.views import AuthenticateTemplateView


class CrfFieldUpdateView(AuthenticateTemplateView):
    permission_required = "study.view_study_detail"
    raise_exception = True
    template_name = "crf/field_form.html"
    layout_nav_key = "STUDIES"
    layout_show_breadcrumb_trail = False
    read_model_service_class = FormBuilderReadModelService
    orchestration_service_class = FormBuilderOrchestrationService

    def get_read_model_service(self):
        return self.read_model_service_class()

    def get_orchestration_service(self):
        return self.orchestration_service_class()

    def get_selected_study_id(self):
        return StudyDropdownHandler(request=self.request).build().selected_id

    def get_field(self):
        if not hasattr(self, "_field"):
            self._field = self.get_orchestration_service().repository.get_field_aggregate_by_scope(
                study_id=self.get_selected_study_id(),
                field_id=self.kwargs["field_id"],
            )
        return self._field

    def get_builder(self):
        if not hasattr(self, "_builder"):
            field = self.get_field()
            if field is None:
                raise Http404
            self._builder = self.get_read_model_service().get_builder(form_id=field.crf_template_id)
        return self._builder

    def ensure_study_scope(self, builder):
        selected_study_id = self.get_selected_study_id()
        if selected_study_id is None:
            raise Http404
        if int(builder["template"]["study_id"]) != int(selected_study_id):
            raise Http404
        return selected_study_id

    def get_initial_data(self, field):
        definition = getattr(field, "definition", None)
        ui_config = getattr(field, "ui_config", None)
        rules = list(field.validation_rules.all())

        return {
            "field_key": field.field_key,
            "data_type": field.data_type,
            "is_active": field.is_active,
            "display_order": field.display_order,
            "section_template_id": field.section_template_id,
            "label_en": field.safe_translation_getter("label", default="", language_code="en") if hasattr(field, "safe_translation_getter") else "",
            "label_vi": field.safe_translation_getter("label", default="", language_code="vi") if hasattr(field, "safe_translation_getter") else "",
            "sdtm": definition.sdtm if definition else "",
            "unit": definition.unit if definition else "",
            "range_min": definition.range_min if definition else None,
            "range_max": definition.range_max if definition else None,
            "precision": definition.precision if definition else None,
            "allowed_missing_values": definition.allowed_missing_values if definition else "",
            "codelist": definition.codelist if definition else "",
            "data_semantic": definition.data_semantic if definition else "",
            "comments": definition.comments if definition else "",
            "text_max_length": definition.text_max_length if definition else None,
            "text_min_length": definition.text_min_length if definition else None,
            "pattern": definition.pattern if definition else "",
            "pattern_err_msg": definition.pattern_err_msg if definition else "",
            "control_type": ui_config.control_type if ui_config else "TEXT_INPUT",
            "layout": ui_config.layout if ui_config else "",
            "text": ui_config.text if ui_config else "",
            "behavior": ui_config.behavior if ui_config else "",
            "options": ui_config.options if ui_config else "",
            "style": ui_config.style if ui_config else "",
            "validation_rules_json": json.dumps([
                {
                    "id": rule.pk,
                    "rule_type": rule.rule_type,
                    "expression": rule.expression,
                    "severity": rule.severity,
                    "mode": rule.mode,
                    "messages": {
                        str(translation.language_code).strip().lower(): translation.message or ""
                        for translation in getattr(rule, "translations", []).all()
                    } or {
                        "en": rule.safe_translation_getter("message", default="", language_code="en") if hasattr(rule, "safe_translation_getter") else "",
                    },
                }
                for rule in rules
            ], ensure_ascii=False),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        builder = self.get_builder()
        selected_study_id = self.ensure_study_scope(builder)
        field = self.get_field()
        if field is None:
            raise Http404

        context.update(builder)
        context["layout_breadcrumb_label"] = field.field_key
        context["page_title"] = field.field_key
        context["field_obj"] = field
        context["field_form_action"] = reverse("crf:field_update", kwargs={"field_id": field.pk})
        context["field_form_mode"] = "update"
        context["field_form_title"] = "Update Field"
        form = kwargs.get("field_form") or CrfFieldUpdateForm(initial=self.get_initial_data(field))
        form = self.apply_section_choices(form, builder)
        context["field_form"] = form
        context["builder_json"] = json.dumps(builder, ensure_ascii=False, indent=2, default=str)
        context["selected_study_id"] = selected_study_id
        return context

    def post(self, request, *args, **kwargs):
        builder = self.get_builder()
        selected_study_id = self.ensure_study_scope(builder)
        field = self.get_field()
        if field is None:
            raise Http404

        form = CrfFieldUpdateForm(request.POST)
        form = self.apply_section_choices(form, builder)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(field_form=form))

        command = to_update_field_aggregate_command(
            selected_study_id=int(selected_study_id),
            study_id=int(selected_study_id),
            field_id=field.pk,
            actor_user_id=request.user.pk,
            ip_address=build_audit_request_context(request)["ip_address"],
            user_agent=build_audit_request_context(request)["user_agent"],
            field_key=form.cleaned_data["field_key"],
            data_type=form.cleaned_data["data_type"],
            is_active=form.cleaned_data.get("is_active", True),
            display_order=form.cleaned_data.get("display_order", 1),
            section_template_id=form.cleaned_data.get("section_template_id"),
            label_en=form.cleaned_data.get("label_en", "") or "",
            label_vi=form.cleaned_data.get("label_vi", "") or "",
            definition=form.get_definition_payload(),
            ui_config=form.get_ui_config_payload(),
            validation_rules=form.cleaned_data.get("validation_rules_json", []),
        )

        try:
            self.get_orchestration_service().update_field(command=command)
        except StudyScopeViolationError as exc:
            raise Http404 from exc
        except FormBuilderDomainValidationError as exc:
            CrfFormBuilderView._bind_field_domain_error(form, exc)
            return self.render_to_response(self.get_context_data(field_form=form))
        except IntegrityError as exc:
            CrfFormBuilderView._bind_field_domain_error(form, exc)
            return self.render_to_response(self.get_context_data(field_form=form))

        return redirect(reverse("crf:form_builder", kwargs={"form_id": field.crf_template_id}))
