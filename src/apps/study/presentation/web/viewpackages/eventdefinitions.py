from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.shared.views.generic import AuthenticateTemplateView
from apps.study.application import (
    EventFormBindingImportDependencyError,
    EventFormBindingImportFormatError,
    EventDefinitionImportDependencyError,
    EventDefinitionImportFormatError,
    ImportStudyEventFormBindingsTemplateCommand,
    ImportStudyEventFormBindingsTemplateService,
    ImportStudyEventDefinitionsTemplateCommand,
    ImportStudyEventDefinitionsTemplateService,
    StudyDirectoryQueryService,
    StudyEventDefinitionDirectoryQueryService,
    StudyNotFoundError,
)
from apps.study.infrastructure.persistence.models import Study
from apps.study.presentation.web.forms import (
    EventDefinitionImportTemplateForm,
    EventFormBindingImportTemplateForm,
)
from apps.study.presentation.web.viewpackages._helpers import _user_has_study_access

__all__ = [
    "StudyEventDefinitionListView",
    "StudyEventDefinitionCreateView",
    "StudyEventDefinitionImportTemplateView",
    "StudyEventFormBindingImportTemplateView",
]


class StudyEventDefinitionListView(LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView):
    permission_required = "study.view_study_detail"
    raise_exception = True
    template_name = "study/event_definitions.html"
    layout_nav_key = "STUDIES"
    study_directory_query_service_class = StudyDirectoryQueryService
    study_event_definition_directory_query_service_class = StudyEventDefinitionDirectoryQueryService
    import_event_definitions_template_service_class = ImportStudyEventDefinitionsTemplateService
    import_event_form_bindings_template_service_class = ImportStudyEventFormBindingsTemplateService
    expected_import_columns = ImportStudyEventDefinitionsTemplateService.expected_columns
    expected_binding_import_columns = ImportStudyEventFormBindingsTemplateService.expected_columns
    _detail_view_model = None
    _study = None

    def get_study_directory_query_service(self):
        return self.study_directory_query_service_class()

    def get_study_event_definition_directory_query_service(self):
        return self.study_event_definition_directory_query_service_class()

    def get_import_event_definitions_template_service(self):
        return self.import_event_definitions_template_service_class()

    def get_import_event_form_bindings_template_service(self):
        return self.import_event_form_bindings_template_service_class()

    def dispatch(self, request, *args, **kwargs):
        self._study = Study.objects.filter(pk=kwargs["study_id"], deleted=False).first()
        if self._study is None:
            raise Http404

        try:
            self._detail_view_model = self.get_study_directory_query_service().get_study_detail(
                study_id=kwargs["study_id"]
            )
        except StudyNotFoundError as exc:
            raise Http404 from exc

        if not _user_has_study_access(request.user, kwargs["study_id"]):
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)

    def get_layout_breadcrumb_label(self):
        if self._detail_view_model is None:
            return super().get_layout_breadcrumb_label()
        return self._detail_view_model["layout_breadcrumb_label"]

    def get_layout_show_breadcrumb_trail(self):
        return False

    def get_layout_detail_meta_items(self):
        if self._detail_view_model is None:
            return super().get_layout_detail_meta_items()
        return self._detail_view_model.get("layout_detail_meta_items", ())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["detail_study"] = self._detail_view_model["detail_study"]
        context.update(
            self.get_study_event_definition_directory_query_service().list_event_definitions(
                study_id=self._study.pk,
                search_query=self.request.GET.get("q", ""),
                sort_key=self.request.GET.get("sort", "sequence_no"),
                sort_direction=self.request.GET.get("direction", "asc"),
            )
        )
        context.setdefault("import_form", EventDefinitionImportTemplateForm())
        context.setdefault("binding_import_form", EventFormBindingImportTemplateForm())
        context["expected_import_columns"] = self.expected_import_columns
        context["expected_binding_import_columns"] = self.expected_binding_import_columns
        context["import_result"] = kwargs.get("import_result")
        context["binding_import_result"] = kwargs.get("binding_import_result")
        context["import_modal_open"] = kwargs.get(
            "import_modal_open",
            self.request.GET.get("open_import_modal") == "1",
        )
        context["binding_import_modal_open"] = kwargs.get(
            "binding_import_modal_open",
            self.request.GET.get("open_binding_import_modal") == "1",
        )
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.has_perm("study.create_study_eventdefinition"):
            raise PermissionDenied

        import_form = EventDefinitionImportTemplateForm(request.POST, request.FILES)
        if not import_form.is_valid():
            return self.render_to_response(
                self.get_context_data(import_form=import_form, import_modal_open=True)
            )

        uploaded_file = import_form.cleaned_data["import_file"]
        command = ImportStudyEventDefinitionsTemplateCommand(
            actor_user_id=request.user.pk,
            file_name=uploaded_file.name,
            file_content=uploaded_file.read(),
        )
        try:
            import_result = self.get_import_event_definitions_template_service().execute(command)
        except (EventDefinitionImportDependencyError, EventDefinitionImportFormatError) as exc:
            import_form.add_error(None, str(exc))
            return self.render_to_response(
                self.get_context_data(import_form=import_form, import_modal_open=True)
            )

        if import_result.skipped_count > 0 or import_result.warnings:
            return self.render_to_response(
                self.get_context_data(
                    import_form=EventDefinitionImportTemplateForm(),
                    import_result=import_result,
                    import_modal_open=True,
                )
            )

        return redirect(
            reverse("study:study_event_definitions", kwargs={"study_id": self._study.pk})
        )


class StudyEventDefinitionCreateView(LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView):
    permission_required = "study.create_study_eventdefinition"
    raise_exception = True
    template_name = "study/event_definition_form.html"
    layout_nav_key = "STUDIES"
    study_directory_query_service_class = StudyDirectoryQueryService
    _detail_view_model = None
    _study = None

    def get_study_directory_query_service(self):
        return self.study_directory_query_service_class()

    def dispatch(self, request, *args, **kwargs):
        self._study = Study.objects.filter(pk=kwargs["study_id"], deleted=False).first()
        if self._study is None:
            raise Http404

        try:
            self._detail_view_model = self.get_study_directory_query_service().get_study_detail(
                study_id=kwargs["study_id"]
            )
        except StudyNotFoundError as exc:
            raise Http404 from exc

        if not _user_has_study_access(request.user, kwargs["study_id"]):
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)

    def get_layout_breadcrumb_label(self):
        return _("NEW EVENT DEFINITION")

    def get_layout_show_breadcrumb_trail(self):
        return False

    def get_layout_detail_meta_items(self):
        if self._detail_view_model is None:
            return super().get_layout_detail_meta_items()
        return self._detail_view_model.get("layout_detail_meta_items", ())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["detail_study"] = self._detail_view_model["detail_study"]
        context["form_title"] = _("New Event Definition")
        context["back_url"] = reverse("study:study_event_definitions", kwargs={"study_id": self._study.pk})
        return context


class StudyEventDefinitionImportTemplateView(StudyEventDefinitionListView):
    permission_required = "study.create_study_eventdefinition"
    raise_exception = True

    def get(self, request, *args, **kwargs):
        return redirect(
            reverse("study:study_event_definitions", kwargs={"study_id": self._study.pk}) + "?open_import_modal=1"
        )


class StudyEventFormBindingImportTemplateView(StudyEventDefinitionListView):
    permission_required = "study.create_study_eventdefinition"
    raise_exception = True

    def get(self, request, *args, **kwargs):
        return redirect(
            reverse("study:study_event_definitions", kwargs={"study_id": self._study.pk}) + "?open_binding_import_modal=1"
        )

    def post(self, request, *args, **kwargs):
        if not request.user.has_perm("study.create_study_eventdefinition"):
            raise PermissionDenied

        binding_import_form = EventFormBindingImportTemplateForm(request.POST, request.FILES)
        if not binding_import_form.is_valid():
            return self.render_to_response(
                self.get_context_data(
                    binding_import_form=binding_import_form,
                    binding_import_modal_open=True,
                )
            )

        uploaded_file = binding_import_form.cleaned_data["import_file"]
        command = ImportStudyEventFormBindingsTemplateCommand(
            actor_user_id=request.user.pk,
            study_id=self._study.pk,
            file_name=uploaded_file.name,
            file_content=uploaded_file.read(),
        )
        try:
            binding_import_result = self.get_import_event_form_bindings_template_service().execute(command)
        except (EventFormBindingImportDependencyError, EventFormBindingImportFormatError) as exc:
            binding_import_form.add_error(None, str(exc))
            return self.render_to_response(
                self.get_context_data(
                    binding_import_form=binding_import_form,
                    binding_import_modal_open=True,
                )
            )

        if binding_import_result.skipped_count > 0 or binding_import_result.warnings:
            return self.render_to_response(
                self.get_context_data(
                    binding_import_form=EventFormBindingImportTemplateForm(),
                    binding_import_result=binding_import_result,
                    binding_import_modal_open=True,
                )
            )

        return redirect(
            reverse("study:study_event_definitions", kwargs={"study_id": self._study.pk})
        )
