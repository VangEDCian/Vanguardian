import json

from django.db import IntegrityError
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse

from apps.audit.public import build_audit_request_context
from apps.crf.application.form_builder_audit import CrfFormBuilderAuditService
from apps.crf.application.form_builder_orchestration import (
    FormBuilderOrchestrationService,
    StudyScopeViolationError,
)
from apps.crf.application.form_builder_queries import FormBuilderReadModelService
from apps.crf.application.services import CrfTemplateApplicationService
from apps.crf.domain.exceptions import FormBuilderDomainValidationError
from apps.crf.presentation.web.forms import (
    CrfFieldCreateForm,
    CrfSectionTemplateForm,
    CrfTemplateTranslationForm,
)
from apps.crf.presentation.web.mappers.form_builder_commands import to_save_field_aggregate_command
from apps.crf.presentation.web.views.builder_support import CrfFormBuilderSupportMixin
from apps.shared.views import AuthenticateTemplateView
from apps.study.application import StudyDirectoryQueryService, StudyNotFoundError


class CrfFormBuilderView(
    CrfFormBuilderSupportMixin,
    AuthenticateTemplateView,
):
    permission_required = "study.view_study_detail"
    raise_exception = True
    template_name = "crf/form_builder.html"
    layout_nav_key = "STUDIES"
    layout_show_breadcrumb_trail = False
    read_model_service_class = FormBuilderReadModelService
    orchestration_service_class = FormBuilderOrchestrationService
    template_service_class = CrfTemplateApplicationService
    audit_service_class = CrfFormBuilderAuditService
    study_directory_query_service_class = StudyDirectoryQueryService
    section_form_prefix = "section"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        builder = self.get_builder()
        selected_study_id = self.ensure_study_scope(builder)
        try:
            study_detail_model = self.get_study_directory_query_service().get_study_detail(
                study_id=selected_study_id,
            )
        except StudyNotFoundError as exc:
            raise Http404 from exc

        context.update(builder)
        context["detail_study"] = study_detail_model["detail_study"]
        context["layout_breadcrumb_label"] = study_detail_model["layout_breadcrumb_label"]
        context["layout_detail_meta_items"] = study_detail_model["layout_detail_meta_items"]
        context["page_title"] = builder["template"]["name"] or builder["template"]["code"]
        context["builder_json"] = json.dumps(builder, ensure_ascii=False, indent=2, default=str)
        context["selected_section_id"] = self.get_selected_section_id()
        context["selected_section"] = self.get_selected_section(builder)
        context["selected_field_id"] = self.get_selected_field_id()
        context["selected_field"] = self.get_selected_field(builder)
        if hasattr(self, "_create_field_form"):
            create_field_form = self.apply_section_choices(self.get_create_field_form(), builder)
        else:
            selected_field_initial = self.get_selected_field_initial(builder)
            if selected_field_initial:
                create_field_form = self.apply_section_choices(CrfFieldCreateForm(initial=selected_field_initial), builder)
            else:
                create_field_form = self.apply_section_choices(self.get_create_field_form(), builder)
        context["field_form_submit_label"] = "Update Field" if (create_field_form.data.get("field_id") or self.get_selected_field_id()) else "Create Field"
        context.setdefault("create_field_form", create_field_form)
        context.setdefault("update_field_form", self.apply_section_choices(self.get_update_field_form(), builder))
        context.setdefault(
            "template_translation_form",
            self.get_template_translation_form(initial=self.get_template_translation_initial(builder)),
        )
        context.setdefault(
            "section_template_form",
            self.get_section_template_form(initial=self.get_section_template_initial(builder)),
        )
        return context

    def post(self, request, *args, **kwargs):  # noqa: C901
        builder = self.get_builder()
        selected_study_id = self.ensure_study_scope(builder)

        action = (request.POST.get("builder_action") or "field").strip()
        if action == "delete-field":
            field_id = self._parse_optional_int(request.POST.get("delete_field_id") or request.POST.get("field_id"))
            if field_id is None:
                raise Http404

            field = self.get_orchestration_service().repository.get_field_aggregate_by_scope(
                study_id=int(selected_study_id),
                field_id=field_id,
            )
            if field is None:
                raise Http404

            before_data = self.get_orchestration_service()._model_metadata_snapshot(field)
            deleted_field = self.get_orchestration_service().repository.delete_field_aggregate(
                study_id=int(selected_study_id),
                form_id=self.kwargs["form_id"],
                field_id=field_id,
                actor_user_id=request.user.pk,
            )
            if deleted_field is None:
                raise Http404

            self.get_audit_service().record_field_deleted(
                study_id=int(selected_study_id),
                form_id=self.kwargs["form_id"],
                field_template_id=field.pk,
                before_data=before_data,
                **build_audit_request_context(request),
            )
            return redirect(reverse("crf:form_builder", kwargs={"form_id": self.kwargs["form_id"]}))

        if action == "delete-section":
            section_id = self._parse_optional_int(request.POST.get("delete_section_id") or request.POST.get("section_id"))
            if section_id is None:
                raise Http404

            section = None
            for candidate in builder.get("sections", []):
                if int(candidate.get("id") or 0) == section_id:
                    section = candidate
                    break

            if section is None:
                raise Http404

            deleted_section = self.get_orchestration_service().repository.delete_section_template(
                study_id=int(selected_study_id),
                form_id=self.kwargs["form_id"],
                section_id=section_id,
                actor_user_id=request.user.pk,
            )
            if deleted_section is None:
                raise Http404

            self.get_audit_service().record_section_template_deleted(
                study_id=int(selected_study_id),
                form_id=self.kwargs["form_id"],
                section_object_id=section_id,
                before_data={
                    "section_code": section.get("section_code", ""),
                    "display_order": section.get("display_order", 1),
                    "is_required": section.get("is_required", True),
                    "is_repeatable": section.get("is_repeatable", False),
                },
                **build_audit_request_context(request),
            )
            return redirect(reverse("crf:form_builder", kwargs={"form_id": self.kwargs["form_id"]}))

        if action == "template":
            form = CrfTemplateTranslationForm(request.POST)
            if not form.is_valid():
                self._template_translation_form = form
                return self.render_to_response(self.get_context_data())

            try:
                self.get_template_service().upsert_crf_template(
                    selected_study_id=int(selected_study_id),
                    study_id=int(selected_study_id),
                    code=form.cleaned_data["code"],
                    version=form.cleaned_data["version"],
                    vi_name=form.cleaned_data.get("name_vi", "") or "",
                    en_name=form.cleaned_data.get("name_en", "") or "",
                    actor_user_id=request.user.pk,
                )
                self.get_audit_service().record_template_saved(
                    study_id=int(selected_study_id),
                    template_id=form.cleaned_data.get("template_id") or self.kwargs["form_id"],
                    after_data={
                        "code": form.cleaned_data["code"],
                        "version": form.cleaned_data["version"],
                        "name_en": form.cleaned_data.get("name_en", "") or "",
                        "name_vi": form.cleaned_data.get("name_vi", "") or "",
                    },
                    **build_audit_request_context(request),
                )
            except StudyScopeViolationError as exc:
                raise Http404 from exc

            return redirect(reverse("crf:form_builder", kwargs={"form_id": self.kwargs["form_id"]}))

        if action == "section":
            form = CrfSectionTemplateForm(request.POST, prefix=self.section_form_prefix)
            if not form.is_valid():
                self._section_template_form = self.apply_section_choices(form, builder)
                return self.render_to_response(self.get_context_data())

            try:
                section_template = self.get_template_service().upsert_section_template(
                    selected_study_id=int(selected_study_id),
                    crf_template_id=self.kwargs["form_id"],
                    section_template_id=form.cleaned_data.get("section_template_id"),
                    section_code=form.cleaned_data["section_code"],
                    vi_name=form.cleaned_data.get("section_name_vi", "") or "",
                    en_name=form.cleaned_data.get("section_name_en", "") or "",
                    vi_description=form.cleaned_data.get("description_vi", "") or "",
                    en_description=form.cleaned_data.get("description_en", "") or "",
                    vi_help_text=form.cleaned_data.get("help_text_vi", "") or "",
                    en_help_text=form.cleaned_data.get("help_text_en", "") or "",
                    vi_instruction_text=form.cleaned_data.get("instruction_text_vi", "") or "",
                    en_instruction_text=form.cleaned_data.get("instruction_text_en", "") or "",
                    display_order=form.cleaned_data.get("display_order", 1),
                    is_required=form.cleaned_data.get("is_required", True),
                    is_repeatable=form.cleaned_data.get("is_repeatable", False),
                    min_repeats=form.cleaned_data.get("min_repeats", 0),
                    max_repeats=form.cleaned_data.get("max_repeats"),
                    actor_user_id=request.user.pk,
                )
                self.get_audit_service().record_section_template_saved(
                    study_id=int(selected_study_id),
                    form_id=self.kwargs["form_id"],
                    section_object_id=form.cleaned_data.get("section_template_id") or form.cleaned_data["section_code"],
                    after_data={
                        "section_code": form.cleaned_data["section_code"],
                        "display_order": form.cleaned_data.get("display_order", 1),
                        "is_required": form.cleaned_data.get("is_required", True),
                        "is_repeatable": form.cleaned_data.get("is_repeatable", False),
                    },
                    **build_audit_request_context(request),
                )
            except StudyScopeViolationError as exc:
                raise Http404 from exc

            return redirect(
                f"{reverse('crf:form_builder', kwargs={'form_id': self.kwargs['form_id']})}?section_id={section_template.pk}"
            )

        form = CrfFieldCreateForm(request.POST)
        self.apply_section_choices(form, builder)
        if not form.is_valid():
            self._create_field_form = form
            self._section_template_form = CrfSectionTemplateForm(
                initial=self.get_section_template_initial(builder),
                prefix=self.section_form_prefix,
            )
            return self.render_to_response(self.get_context_data())

        command = to_save_field_aggregate_command(
            selected_study_id=int(selected_study_id),
            study_id=int(selected_study_id),
            form_id=self.kwargs["form_id"],
            actor_user_id=request.user.pk,
            ip_address=build_audit_request_context(request)["ip_address"],
            user_agent=build_audit_request_context(request)["user_agent"],
            field_id=form.cleaned_data.get("field_id"),
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
            self.get_orchestration_service().save_field(command=command)
        except StudyScopeViolationError as exc:
            raise Http404 from exc
        except FormBuilderDomainValidationError as exc:
            self._bind_field_domain_error(form, exc)
            self._create_field_form = form
            self._section_template_form = CrfSectionTemplateForm(
                initial=self.get_section_template_initial(builder),
                prefix=self.section_form_prefix,
            )
            return self.render_to_response(self.get_context_data())
        except IntegrityError as exc:
            # Defensive fallback for DB unique constraints (e.g., case-insensitive duplicates).
            self._bind_field_domain_error(form, exc)
            self._create_field_form = form
            self._section_template_form = CrfSectionTemplateForm(
                initial=self.get_section_template_initial(builder),
                prefix=self.section_form_prefix,
            )
            return self.render_to_response(self.get_context_data())

        return redirect(reverse("crf:form_builder", kwargs={"form_id": self.kwargs["form_id"]}))
