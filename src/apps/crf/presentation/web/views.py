import json

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse

from apps.crf.application.form_builder_orchestration import (
    CreateFieldAggregateCommand,
    FormBuilderOrchestrationService,
    SaveFieldAggregateCommand,
    StudyScopeViolationError,
    UpdateFieldAggregateCommand,
)
from apps.crf.application.form_builder_audit import CrfFormBuilderAuditService
from apps.crf.application.form_builder_queries import FormBuilderReadModelService
from apps.crf.application.services import CrfTemplateApplicationService
from apps.crf.domain.exceptions import FormBuilderDomainValidationError, FormScopeViolationError
from apps.crf.presentation.web.forms import CrfFieldCreateForm, CrfFieldUpdateForm, CrfSectionTemplateForm, CrfTemplateTranslationForm
from apps.shared.context_processors import StudyDropdownHandler
from apps.shared.views import AuthenticateTemplateView


class CrfFormDetailView(LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView):
    permission_required = "study.view_study_detail"
    raise_exception = True
    template_name = "crf/form_detail.html"
    layout_nav_key = "STUDIES"
    layout_show_breadcrumb_trail = False
    read_model_service_class = FormBuilderReadModelService

    def get_read_model_service(self):
        return self.read_model_service_class()

    def get_selected_study_id(self):
        return StudyDropdownHandler(request=self.request).build().selected_id

    def get_builder(self):
        if not hasattr(self, "_builder"):
            try:
                self._builder = self.get_read_model_service().get_builder(
                    form_id=self.kwargs["form_id"],
                )
            except FormScopeViolationError as exc:
                raise Http404 from exc
        return self._builder

    def ensure_study_scope(self, builder):
        selected_study_id = self.get_selected_study_id()
        if selected_study_id is None:
            raise Http404
        if int(builder["template"]["study_id"]) != int(selected_study_id):
            raise Http404
        return selected_study_id

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        builder = self.get_builder()
        selected_study_id = self.ensure_study_scope(builder)

        context.update(builder)
        context["detail_study"] = {"id": int(selected_study_id)}
        context["layout_breadcrumb_label"] = builder["template"]["code"]
        context["page_title"] = builder["template"]["name"] or builder["template"]["code"]
        context["fields_total"] = len(builder.get("fields", []))
        context["sections_total"] = len([section for section in builder.get("sections", []) if section.get("id") is not None])
        return context


class CrfFormBuilderView(LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView):
    permission_required = "study.view_study_detail"
    raise_exception = True
    template_name = "crf/form_builder.html"
    layout_nav_key = "STUDIES"
    layout_show_breadcrumb_trail = False
    read_model_service_class = FormBuilderReadModelService
    orchestration_service_class = FormBuilderOrchestrationService
    template_service_class = CrfTemplateApplicationService
    audit_service_class = CrfFormBuilderAuditService
    section_form_prefix = "section"

    @staticmethod
    def _bind_field_domain_error(form, exc):
        message = str(exc or "")
        normalized_message = message.lower()
        is_duplicate_field_key = (
            "field_key must be unique in form scope." in message
            or "crf_fieldtemplate_crf_template_fieldkey_uniq" in normalized_message
            or "duplicate entry" in normalized_message and "fieldkey" in normalized_message
        )

        if is_duplicate_field_key:
            form.add_error("field_key", "Field Key da ton tai trong form nay.")
            return

        form.add_error(None, message)

    def get_read_model_service(self):
        return self.read_model_service_class()

    def get_orchestration_service(self):
        return self.orchestration_service_class()

    def get_template_service(self):
        return self.template_service_class()

    def get_audit_service(self):
        return self.audit_service_class()

    def get_create_field_form(self):
        if not hasattr(self, "_create_field_form"):
            self._create_field_form = CrfFieldCreateForm()
        return self._create_field_form

    def get_update_field_form(self):
        if not hasattr(self, "_update_field_form"):
            self._update_field_form = CrfFieldUpdateForm()
        return self._update_field_form

    def get_section_template_form(self, *, initial=None):
        if not hasattr(self, "_section_template_form"):
            self._section_template_form = CrfSectionTemplateForm(initial=initial, prefix=self.section_form_prefix)
        return self._section_template_form

    def get_template_translation_form(self, *, initial=None):
        if not hasattr(self, "_template_translation_form"):
            self._template_translation_form = CrfTemplateTranslationForm(initial=initial)
        return self._template_translation_form

    def get_selected_study_id(self):
        return StudyDropdownHandler(request=self.request).build().selected_id

    def get_builder(self):
        if not hasattr(self, "_builder"):
            try:
                self._builder = self.get_read_model_service().get_builder(
                    form_id=self.kwargs["form_id"],
                )
            except FormScopeViolationError as exc:
                raise Http404 from exc
        return self._builder

    def ensure_study_scope(self, builder):
        selected_study_id = self.get_selected_study_id()
        if selected_study_id is None:
            raise Http404
        if int(builder["template"]["study_id"]) != int(selected_study_id):
            raise Http404
        return selected_study_id

    def get_section_choices(self, builder):
        sections = builder.get("sections", [])
        choices = []
        for section in sections:
            section_id = section.get("id")
            if section_id is None:
                continue
            choices.append((str(section_id), f'{section.get("section_code", "")}: {section.get("section_name", "")}'))
        return choices

    def get_section_template_initial(self, builder):
        section_id = self.request.GET.get("section_id")
        if not section_id:
            return {}

        for section in builder.get("sections", []):
            if str(section.get("id")) != str(section_id):
                continue

            translations = section.get("translations", {}) or {}
            en_translation = translations.get("en", {}) or {}
            vi_translation = translations.get("vi", {}) or {}
            return {
                "section_template_id": section.get("id"),
                "section_code": section.get("section_code", ""),
                "section_name_en": en_translation.get("section_name", section.get("section_name", "")),
                "section_name_vi": vi_translation.get("section_name", section.get("section_name", "")),
                "description_en": en_translation.get("description", ""),
                "description_vi": vi_translation.get("description", ""),
                "help_text_en": en_translation.get("help_text", ""),
                "help_text_vi": vi_translation.get("help_text", ""),
                "instruction_text_en": en_translation.get("instruction_text", ""),
                "instruction_text_vi": vi_translation.get("instruction_text", ""),
                "display_order": section.get("display_order", 1),
                "is_required": section.get("is_required", True),
                "is_repeatable": section.get("is_repeatable", False),
                "min_repeats": section.get("min_repeats", 0),
                "max_repeats": section.get("max_repeats"),
            }

        return {}

    def get_template_translation_initial(self, builder):
        template = builder.get("template", {}) or {}
        translations = template.get("translations", {}) or {}
        en_translation = translations.get("en", "") if isinstance(translations.get("en"), str) else translations.get("en", {})
        vi_translation = translations.get("vi", "") if isinstance(translations.get("vi"), str) else translations.get("vi", {})
        return {
            "template_id": template.get("id"),
            "code": template.get("code", ""),
            "version": template.get("version", ""),
            "name_en": en_translation if isinstance(en_translation, str) else template.get("name", ""),
            "name_vi": vi_translation if isinstance(vi_translation, str) else template.get("name", ""),
        }

    @staticmethod
    def _parse_optional_int(raw_value):
        if raw_value in (None, ""):
            return None
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return None

    def get_selected_field_id(self):
        raw_value = self.request.GET.get("field_id") or self.request.POST.get("field_id")
        if raw_value in (None, ""):
            return None
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return None

    def get_selected_section_id(self):
        raw_value = self.request.GET.get("section_id") or self.request.POST.get("section_id")
        if raw_value in (None, ""):
            return None
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return None

    def get_selected_section(self, builder):
        selected_section_id = self.get_selected_section_id()
        if selected_section_id is None:
            return None

        for section in builder.get("sections", []):
            if int(section.get("id") or 0) == selected_section_id:
                return section

        return None

    def get_selected_field(self, builder):
        selected_field_id = self.get_selected_field_id()
        if selected_field_id is None:
            return None

        for field in builder.get("fields", []):
            if int(field.get("id") or 0) == selected_field_id:
                return field

        return None

    def get_selected_field_initial(self, builder):
        selected_field_id = self.get_selected_field_id()
        if selected_field_id is None:
            return {}

        for field in builder.get("fields", []):
            if int(field.get("id") or 0) != selected_field_id:
                continue

            field_template = field.get("field_template", {}) or {}
            field_definition = field.get("field_definition", {}) or {}
            field_ui_config = field.get("field_ui_config", {}) or {}
            validation_rules = field.get("field_validation_rules", []) or []
            translations = field_template.get("translations", {}) or {}
            return {
                "field_id": field.get("id"),
                "field_key": field_template.get("field_key", ""),
                "data_type": field_template.get("data_type", ""),
                "is_active": field_template.get("is_active", True),
                "display_order": field_template.get("display_order", 1),
                "section_template_id": field_template.get("section_template_id"),
                "label_en": translations.get("en", field_template.get("label", "")),
                "label_vi": translations.get("vi", field_template.get("label", "")),
                "sdtm": json.dumps(field_definition.get("sdtm") or {}, ensure_ascii=False),
                "unit": field_definition.get("unit", "") or "",
                "range_min": field_definition.get("range_min"),
                "range_max": field_definition.get("range_max"),
                "precision": field_definition.get("precision"),
                "allowed_missing_values": field_definition.get("allowed_missing_values", "") or "",
                "codelist": field_definition.get("codelist", "") or "",
                "data_semantic": field_definition.get("data_semantic", "") or "",
                "comments": field_definition.get("comments", "") or "",
                "text_max_length": field_definition.get("text_max_length"),
                "text_min_length": field_definition.get("text_min_length"),
                "pattern": field_definition.get("pattern", "") or "",
                "pattern_err_msg": field_definition.get("pattern_err_msg", "") or "",
                "control_type": field_ui_config.get("control_type", "") or "",
                "layout": field_ui_config.get("layout", "") or "",
                "text": field_ui_config.get("text", "") or "",
                "behavior": field_ui_config.get("behavior", "") or "",
                "options": field_ui_config.get("options", "") or "",
                "style": field_ui_config.get("style", "") or "",
                "validation_rules_json": json.dumps([
                    {
                        "id": rule.get("id"),
                        "rule_type": rule.get("rule_type"),
                        "expression": rule.get("expression"),
                        "severity": rule.get("severity"),
                        "mode": rule.get("mode"),
                        "messages": rule.get("messages", {}) or {},
                    }
                    for rule in validation_rules
                ], ensure_ascii=False),
            }

        return {}

    def apply_section_choices(self, form, builder):
        choices = self.get_section_choices(builder)
        if hasattr(form, "set_section_template_choices"):
            form.set_section_template_choices(choices)
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        builder = self.get_builder()
        selected_study_id = self.ensure_study_scope(builder)
        context.update(builder)
        context["detail_study"] = {"id": int(selected_study_id)}
        context["layout_breadcrumb_label"] = builder["template"]["code"]
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

    def post(self, request, *args, **kwargs):
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
                request=request,
                study_id=int(selected_study_id),
                form_id=self.kwargs["form_id"],
                field_template_id=field.pk,
                before_data=before_data,
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
                request=request,
                study_id=int(selected_study_id),
                form_id=self.kwargs["form_id"],
                section_object_id=section_id,
                before_data={
                    "section_code": section.get("section_code", ""),
                    "display_order": section.get("display_order", 1),
                    "is_required": section.get("is_required", True),
                    "is_repeatable": section.get("is_repeatable", False),
                },
            )
            return redirect(reverse("crf:form_builder", kwargs={"form_id": self.kwargs["form_id"]}))

        if action == "template":
            form = CrfTemplateTranslationForm(request.POST)
            if not form.is_valid():
                self._template_translation_form = form
                return self.render_to_response(self.get_context_data())

            try:
                self.get_template_service().upsert_crf_template(
                    request=request,
                    study_id=int(selected_study_id),
                    code=form.cleaned_data["code"],
                    version=form.cleaned_data["version"],
                    vi_name=form.cleaned_data.get("name_vi", "") or "",
                    en_name=form.cleaned_data.get("name_en", "") or "",
                    actor_user_id=request.user.pk,
                )
                self.get_audit_service().record_template_saved(
                    request=request,
                    study_id=int(selected_study_id),
                    template_id=form.cleaned_data.get("template_id") or self.kwargs["form_id"],
                    after_data={
                        "code": form.cleaned_data["code"],
                        "version": form.cleaned_data["version"],
                        "name_en": form.cleaned_data.get("name_en", "") or "",
                        "name_vi": form.cleaned_data.get("name_vi", "") or "",
                    },
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
                    request=request,
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
                    request=request,
                    study_id=int(selected_study_id),
                    form_id=self.kwargs["form_id"],
                    section_object_id=form.cleaned_data.get("section_template_id") or form.cleaned_data["section_code"],
                    after_data={
                        "section_code": form.cleaned_data["section_code"],
                        "display_order": form.cleaned_data.get("display_order", 1),
                        "is_required": form.cleaned_data.get("is_required", True),
                        "is_repeatable": form.cleaned_data.get("is_repeatable", False),
                    },
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

        command = SaveFieldAggregateCommand(
            study_id=int(selected_study_id),
            form_id=self.kwargs["form_id"],
            actor_user_id=request.user.pk,
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
            self.get_orchestration_service().save_field(request=request, command=command)
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


class CrfFieldUpdateView(LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView):
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

        command = UpdateFieldAggregateCommand(
            study_id=int(selected_study_id),
            field_id=field.pk,
            actor_user_id=request.user.pk,
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
            self.get_orchestration_service().update_field(request=request, command=command)
        except StudyScopeViolationError as exc:
            raise Http404 from exc
        except FormBuilderDomainValidationError as exc:
            CrfFormBuilderView._bind_field_domain_error(form, exc)
            return self.render_to_response(self.get_context_data(field_form=form))
        except IntegrityError as exc:
            CrfFormBuilderView._bind_field_domain_error(form, exc)
            return self.render_to_response(self.get_context_data(field_form=form))

        return redirect(reverse("crf:form_builder", kwargs={"form_id": field.crf_template_id}))
