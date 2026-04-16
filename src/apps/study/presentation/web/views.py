import datetime

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import ListView
from django_filters.views import FilterView
from django_tables2 import SingleTableMixin

from apps.shared.views import AuthenticateTemplateContextMixin, AuthenticateTemplateView

from apps.study.application import (
    CrfTemplateImportDependencyError,
    CrfTemplateImportFormatError,
    CreateStudyCommand,
    CreateStudyService,
    DeleteStudyCommand,
    DeleteStudyService,
    ImportStudyCrfTemplatesTemplateCommand,
    ImportStudyCrfTemplatesTemplateService,
    StudyAuditService,
    StudyCodeAlreadyExistsError,
    StudyDateRangeError,
    StudyDirectoryQueryService,
    StudyFilterActiveQueryService,
    StudyFilterInactiveQueryService,
    StudyNotFoundError,
    ToggleStudyStatusCommand,
    ToggleStudyStatusService,
    UpdateStudyCommand,
    UpdateStudyService,
)
from apps.crf.public import get_crf_template_model
from apps.study.infrastructure.persistence.models import Study
from apps.study.presentation.web.forms import (
    CrfTemplateImportTemplateForm,
    CrfTemplatesToolbarForm,
    StudyForm,
)
from apps.study.presentation.web.tables import CrfTemplateListTable
from apps.study.presentation.web.viewpackages._helpers import (
    _can_change_study_status,
    _serialize_study_snapshot,
    _user_has_study_access,
)
from apps.study.presentation.web.viewpackages.eventdefinitions import (
    StudyEventDefinitionCreateView,
    StudyEventFormBindingImportTemplateView,
    StudyEventDefinitionImportTemplateView,
    StudyEventDefinitionListView,
)
from apps.study.presentation.web.viewpackages.randomization import (
    StudyRandomizationView,
)
from apps.study.presentation.web.viewpackages.site import (
    SiteListView, SiteDetailView, SiteCreateView, SiteDeleteView,
)

__all__ = [
    "StudyEventDefinitionCreateView",
    "StudyEventFormBindingImportTemplateView",
    "StudyEventDefinitionImportTemplateView",
    "StudyEventDefinitionListView",
    "StudyRandomizationView",

    "SiteListView",
    "SiteDetailView",
    "SiteCreateView",
    "SiteDeleteView",
    "StudyCrfTemplateImportTemplateView",
]

# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


class StudyListView(
    LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView
):
    permission_required = "study.view_study_list"
    raise_exception = True
    template_name = "study/studies.html"
    layout_nav_key = "STUDIES"
    layout_breadcrumb_label = _("STUDIES")
    study_directory_query_service_class = StudyDirectoryQueryService
    registered_filter_query_service_classes = (
        StudyFilterActiveQueryService,
        StudyFilterInactiveQueryService,
    )

    def get_study_directory_query_service(self):
        return self.study_directory_query_service_class(
            registered_filter_query_service_classes=self.registered_filter_query_service_classes
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        can_search = user.has_perm("study.search_study_by_name")
        can_filter_code = user.has_perm("study.filter_study_by_code")
        can_filter_status = user.has_perm("study.filter_study_by_status")

        context.update(
            self.get_study_directory_query_service().list_studies(
                user=user,
                search_query=self.request.GET.get("q", "") if can_search else "",
                code_filter=self.request.GET.get("code", "") if can_filter_code else "",
                filter_key=self.request.GET.get("filter", "")
                if can_filter_status
                else "",
                sort_key=self.request.GET.get("sort", "code"),
                sort_direction=self.request.GET.get("direction", "asc"),
                can_search=can_search,
                can_filter_code=can_filter_code,
                can_filter_status=can_filter_status,
            )
        )
        context["can_search"] = can_search
        context["can_filter_code"] = can_filter_code
        context["can_filter_status"] = can_filter_status
        return context


class StudyDetailView(
    LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView
):
    permission_required = "study.view_study_detail"
    raise_exception = True
    template_name = "study/study_detail.html"
    layout_nav_key = "STUDIES"
    study_directory_query_service_class = StudyDirectoryQueryService
    update_study_service_class = UpdateStudyService
    study_audit_service_class = StudyAuditService
    _detail_view_model = None
    _study = None

    def get_study_directory_query_service(self):
        return self.study_directory_query_service_class()

    def get_update_study_service(self):
        return self.update_study_service_class()

    def get_study_audit_service(self):
        return self.study_audit_service_class()

    def dispatch(self, request, *args, **kwargs):
        self._study = Study.objects.filter(pk=kwargs["study_id"], deleted=False).first()
        if self._study is None:
            raise Http404

        try:
            self._detail_view_model = (
                self.get_study_directory_query_service().get_study_detail(
                    study_id=kwargs["study_id"]
                )
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
        study_id = self._detail_view_model["detail_study"]["id"]

        user = self.request.user
        can_toggle_status = _can_change_study_status(user)
        can_update_field_name = user.has_perm("study.update_study_field_name")
        can_update_field_sponsor = user.has_perm("study.update_study_field_sponsor")
        can_update_field_dates = user.has_perm("study.update_study_field_dates")
        can_update_field_description = user.has_perm(
            "study.update_study_field_description"
        )
        can_update_detail = any((
            can_update_field_name,
            can_update_field_sponsor,
            can_update_field_dates,
            can_update_field_description,
            can_toggle_status,
        ))

        if self._detail_view_model is not None:
            context["detail_study"] = self._detail_view_model["detail_study"]

        context.setdefault(
            "form",
            StudyForm(
                initial={
                    "code": self._study.code,
                    "name": self._study.name,
                    "sponsor": self._study.sponsor,
                    "description": self._study.description,
                    "start_date": self._study.start_date,
                    "end_date": self._study.end_date,
                    "is_active": self._study.is_active,
                }
            ),
        )
        context["can_toggle_status"] = can_toggle_status
        context["can_update_detail"] = can_update_detail
        context["can_delete_study"] = user.has_perm("study.delete_study")
        context["delete_url"] = reverse(
            "study:study_delete", kwargs={"study_id": study_id}
        )

        # Field-level view permissions
        context["can_view_field_code"] = user.has_perm("study.view_study_field_code")
        context["can_view_field_name"] = user.has_perm("study.view_study_field_name")
        context["can_view_field_sponsor"] = user.has_perm(
            "study.view_study_field_sponsor"
        )
        context["can_view_field_dates"] = user.has_perm("study.view_study_field_dates")
        context["can_view_field_description"] = user.has_perm(
            "study.view_study_field_description"
        )
        context["can_update_field_code"] = False
        context["can_update_field_name"] = can_update_field_name
        context["can_update_field_sponsor"] = can_update_field_sponsor
        context["can_update_field_dates"] = can_update_field_dates
        context["can_update_field_description"] = can_update_field_description

        return context

    def post(self, request, *args, **kwargs):
        if not self._can_update_detail(request.user):
            raise PermissionDenied

        form = StudyForm(request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        before_data = _serialize_study_snapshot(self._study)

        command = UpdateStudyCommand(
            study_id=self._study.pk,
            code=self._study.code,
            name=form.cleaned_data["name"]
            if request.user.has_perm("study.update_study_field_name")
            else self._study.name,
            sponsor=form.cleaned_data["sponsor"]
            if request.user.has_perm("study.update_study_field_sponsor")
            else self._study.sponsor,
            description=form.cleaned_data["description"]
            if request.user.has_perm("study.update_study_field_description")
            else self._study.description,
            start_date=form.cleaned_data.get("start_date")
            if request.user.has_perm("study.update_study_field_dates")
            else self._study.start_date,
            end_date=form.cleaned_data.get("end_date")
            if request.user.has_perm("study.update_study_field_dates")
            else self._study.end_date,
            is_active=form.cleaned_data.get("is_active", False)
            if _can_change_study_status(request.user)
            else self._study.is_active,
            actor_user_id=request.user.pk,
        )

        try:
            updated_study = self.get_update_study_service().execute(command)
        except StudyCodeAlreadyExistsError:
            form.add_error("code", _("This study code already exists."))
            return self.render_to_response(self.get_context_data(form=form))
        except StudyDateRangeError:
            form.add_error("end_date", _("End date must be on or after start date."))
            return self.render_to_response(self.get_context_data(form=form))

        self.get_study_audit_service().record_updated(
            request=request,
            study=updated_study,
            before_data=before_data,
        )

        return redirect(
            reverse("study:study_detail", kwargs={"study_id": self._study.pk})
        )

    def _can_update_detail(self, request_user):
        return any((
            request_user.has_perm("study.update_study_field_name"),
            request_user.has_perm("study.update_study_field_sponsor"),
            request_user.has_perm("study.update_study_field_dates"),
            request_user.has_perm("study.update_study_field_description"),
            _can_change_study_status(request_user),
        ))


class StudyCrfTemplateListView(
    LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateContextMixin,
    SingleTableMixin, FilterView, ListView,
):
    permission_required = "study.view_study_detail"
    raise_exception = True
    template_name = "study/crf_templates.html"
    layout_nav_key = "STUDIES"
    model = get_crf_template_model()
    table_class = CrfTemplateListTable
    filterset_class = CrfTemplatesToolbarForm
    context_table_name = "crf_templates_table"
    paginate_by = 25

    study_directory_query_service_class = StudyDirectoryQueryService
    import_crf_templates_template_service_class = ImportStudyCrfTemplatesTemplateService
    expected_import_columns = ImportStudyCrfTemplatesTemplateService.expected_columns
    _detail_view_model = None
    _study = None

    def get_study_directory_query_service(self):
        return self.study_directory_query_service_class()

    def get_import_crf_templates_template_service(self):
        return self.import_crf_templates_template_service_class()

    def dispatch(self, request, *args, **kwargs):
        self._study = Study.objects.filter(pk=kwargs["study_id"], deleted=False).first()
        if self._study is None:
            raise Http404

        try:
            self._detail_view_model = (
                self.get_study_directory_query_service().get_study_detail(
                    study_id=kwargs["study_id"]
                )
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

    def get_queryset(self):
        return super().get_queryset().filter(
            study_id=self._study.pk,
            deleted=False,
        ).prefetch_related("translations")

    def get_table(self, **kwargs):
        table = super().get_table(**kwargs)
        table.empty_text = _("No CRF templates found matching your criteria.")
        return table

    @staticmethod
    def _build_hidden_fields(**params):
        return [{"name": name, "value": value} for name, value in params.items() if value not in (None, "")]

    def _build_table_toolbar(self, *, total, search_query, sort_query):
        return {
            "filter": None,
            "secondary_search": None,
            "summary": {
                "label": _("Total CRF Templates"),
                "value": total,
            },
            "search": {
                "name": "search",
                "value": search_query,
                "placeholder": _("Search CRF templates..."),
                "aria_label": _("Search CRF templates"),
                "show_icon": True,
                "hidden_fields": self._build_hidden_fields(sort=sort_query),
            },
        }

    def _ensure_filter_state(self):
        if not hasattr(self, "filterset"):
            self.filterset = self.get_filterset(self.get_filterset_class())
        if not hasattr(self, "object_list"):
            self.object_list = self.filterset.qs

    def get_context_data(self, **kwargs):
        self._ensure_filter_state()
        context = super().get_context_data(**kwargs)
        context["detail_study"] = self._detail_view_model["detail_study"]
        search_query = (self.request.GET.get("search", "") or "").strip()
        sort_query = self.request.GET.get("sort", "")
        context["crf_templates_total"] = self.filterset.qs.count()
        context["crf_templates_empty_text"] = _("No CRF templates found matching your criteria.")
        context["crf_templates_table_toolbar"] = self._build_table_toolbar(
            total=context["crf_templates_total"],
            search_query=search_query,
            sort_query=sort_query,
        )
        context["crf_template_search_query"] = search_query
        context.setdefault("import_form", CrfTemplateImportTemplateForm())
        context["expected_import_columns"] = self.expected_import_columns
        context["import_result"] = kwargs.get("import_result")
        context["import_modal_open"] = kwargs.get(
            "import_modal_open",
            self.request.GET.get("open_import_modal") == "1",
        )
        return context

    def post(self, request, *args, **kwargs):
        import_form = CrfTemplateImportTemplateForm(request.POST, request.FILES)
        if not import_form.is_valid():
            return self.render_to_response(
                self.get_context_data(import_form=import_form, import_modal_open=True)
            )

        uploaded_file = import_form.cleaned_data["import_file"]
        command = ImportStudyCrfTemplatesTemplateCommand(
            actor_user_id=request.user.pk,
            study_id=self._study.pk,
            file_name=uploaded_file.name,
            file_content=uploaded_file.read(),
        )
        try:
            import_result = self.get_import_crf_templates_template_service().execute(command)
        except (CrfTemplateImportDependencyError, CrfTemplateImportFormatError) as exc:
            import_form.add_error(None, str(exc))
            return self.render_to_response(
                self.get_context_data(import_form=import_form, import_modal_open=True)
            )

        if import_result.skipped_count == 0 and not import_result.warnings:
            return redirect(
                reverse("study:study_crf_templates", kwargs={"study_id": self._study.pk})
            )

        return self.render_to_response(
            self.get_context_data(
                import_form=CrfTemplateImportTemplateForm(),
                import_result=import_result,
                import_modal_open=True,
            )
        )


class StudyCrfTemplateImportTemplateView(StudyCrfTemplateListView):
    raise_exception = True

    def get(self, request, *args, **kwargs):
        return redirect(
            reverse("study:study_crf_templates", kwargs={"study_id": self._study.pk}) + "?open_import_modal=1"
        )


class StudyCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView
):
    permission_required = "study.create_study"
    raise_exception = True
    template_name = "study/study_form.html"
    layout_nav_key = "STUDIES"
    layout_breadcrumb_label = _("NEW STUDY")
    create_study_service_class = CreateStudyService
    study_audit_service_class = StudyAuditService

    def get_create_study_service(self):
        return self.create_study_service_class()

    def get_study_audit_service(self):
        return self.study_audit_service_class()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("form", StudyForm())
        context["form_action"] = reverse("study:study_create")
        context["form_title"] = _("New Study")
        context["back_url"] = reverse("study:study_list")
        context["start_date_min"] = datetime.date.today().strftime("%Y-%m-%d")
        context["can_edit_code"] = True
        context["show_is_active"] = True
        # Create view: admin only, show all fields
        context["can_update_field_code"] = True
        context["can_update_field_name"] = True
        context["can_update_field_sponsor"] = True
        context["can_update_field_dates"] = True
        context["can_update_field_description"] = True
        return context

    def post(self, request, *args, **kwargs):
        form = StudyForm(request.POST)
        if not form.is_valid():
            return self._render_form(request, form)

        start_date = form.cleaned_data.get("start_date")
        if start_date and start_date < datetime.date.today():
            form.add_error("start_date", _("Start date cannot be in the past."))
            return self._render_form(request, form)

        command = CreateStudyCommand(
            code=form.cleaned_data["code"],
            name=form.cleaned_data["name"],
            sponsor=form.cleaned_data["sponsor"],
            description=form.cleaned_data["description"],
            start_date=form.cleaned_data.get("start_date"),
            end_date=form.cleaned_data.get("end_date"),
            is_active=form.cleaned_data.get("is_active", True),
            actor_user_id=request.user.pk,
        )

        try:
            study = self.get_create_study_service().execute(command)
        except StudyCodeAlreadyExistsError:
            form.add_error("code", _("This study code already exists."))
            return self._render_form(request, form)
        except StudyDateRangeError:
            form.add_error("end_date", _("End date must be on or after start date."))
            return self._render_form(request, form)

        self.get_study_audit_service().record_created(request=request, study=study)

        return redirect(reverse("study:study_detail", kwargs={"study_id": study.pk}))

    def _render_form(self, request, form):
        context = self.get_context_data(form=form)
        return self.render_to_response(context)


class StudyUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView
):
    permission_required = "study.update_study"
    raise_exception = True
    template_name = "study/study_form.html"
    layout_nav_key = "STUDIES"
    update_study_service_class = UpdateStudyService
    study_audit_service_class = StudyAuditService
    _study = None

    def dispatch(self, request, *args, **kwargs):
        self._study = Study.objects.filter(pk=kwargs["study_id"], deleted=False).first()
        if self._study is None:
            raise Http404

        if not _user_has_study_access(request.user, kwargs["study_id"]):
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)

    def get_layout_breadcrumb_label(self):
        if self._study is None:
            return super().get_layout_breadcrumb_label()
        return self._study.code

    def get_update_study_service(self):
        return self.update_study_service_class()

    def get_study_audit_service(self):
        return self.study_audit_service_class()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault(
            "form",
            StudyForm(
                initial={
                    "code": self._study.code,
                    "name": self._study.name,
                    "sponsor": self._study.sponsor,
                    "description": self._study.description,
                    "start_date": self._study.start_date,
                    "end_date": self._study.end_date,
                    "is_active": self._study.is_active,
                }
            ),
        )
        user = self.request.user
        context["form_action"] = reverse(
            "study:study_update", kwargs={"study_id": self._study.pk}
        )
        context["form_title"] = self._study.code
        context["back_url"] = reverse(
            "study:study_detail", kwargs={"study_id": self._study.pk}
        )
        context["can_edit_code"] = user.has_perm("study.update_study_field_code")
        context["show_is_active"] = False

        # Field-level update permissions
        context["can_update_field_code"] = user.has_perm(
            "study.update_study_field_code"
        )
        context["can_update_field_name"] = user.has_perm(
            "study.update_study_field_name"
        )
        context["can_update_field_sponsor"] = user.has_perm(
            "study.update_study_field_sponsor"
        )
        context["can_update_field_dates"] = user.has_perm(
            "study.update_study_field_dates"
        )
        context["can_update_field_description"] = user.has_perm(
            "study.update_study_field_description"
        )
        return context

    def post(self, request, *args, **kwargs):
        form = StudyForm(request.POST)
        if not form.is_valid():
            return self._render_form(request, form)

        before_data = _serialize_study_snapshot(self._study)

        code = (
            form.cleaned_data["code"]
            if request.user.has_perm("study.update_study_field_code")
            else self._study.code
        )

        command = UpdateStudyCommand(
            study_id=self._study.pk,
            code=code,
            name=form.cleaned_data["name"],
            sponsor=form.cleaned_data["sponsor"],
            description=form.cleaned_data["description"],
            start_date=form.cleaned_data.get("start_date"),
            end_date=form.cleaned_data.get("end_date"),
            is_active=self._study.is_active,
            actor_user_id=request.user.pk,
        )

        try:
            updated_study = self.get_update_study_service().execute(command)
        except StudyCodeAlreadyExistsError:
            form.add_error("code", _("This study code already exists."))
            return self._render_form(request, form)
        except StudyDateRangeError:
            form.add_error("end_date", _("End date must be on or after start date."))
            return self._render_form(request, form)

        self.get_study_audit_service().record_updated(
            request=request,
            study=updated_study,
            before_data=before_data,
        )

        return redirect(
            reverse("study:study_detail", kwargs={"study_id": self._study.pk})
        )

    def _render_form(self, request, form):
        context = self.get_context_data(form=form)
        return self.render_to_response(context)


class StudyToggleStatusView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """POST-only endpoint. Flips the is_active flag of a study."""

    permission_required = "study.change_study_status"
    raise_exception = True
    toggle_study_status_service_class = ToggleStudyStatusService
    study_audit_service_class = StudyAuditService

    def get_toggle_study_status_service(self):
        return self.toggle_study_status_service_class()

    def get_study_audit_service(self):
        return self.study_audit_service_class()

    def post(self, request, *_args, **kwargs):
        study_id = kwargs["study_id"]
        command = ToggleStudyStatusCommand(
            study_id=study_id,
            actor_user_id=request.user.pk,
        )

        try:
            study = self.get_toggle_study_status_service().execute(command)
        except StudyNotFoundError:
            raise Http404

        self.get_study_audit_service().record_status_changed(
            request=request, study=study
        )

        return redirect(reverse("study:study_detail", kwargs={"study_id": study_id}))


class StudyDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "study.delete_study"
    raise_exception = True
    delete_study_service_class = DeleteStudyService
    study_audit_service_class = StudyAuditService

    def get_delete_study_service(self):
        return self.delete_study_service_class()

    def get_study_audit_service(self):
        return self.study_audit_service_class()

    def post(self, request, *_args, **kwargs):
        study = Study.objects.filter(pk=kwargs["study_id"], deleted=False).first()
        if study is None:
            raise Http404

        if not _user_has_study_access(request.user, study.pk):
            raise PermissionDenied

        before_data = _serialize_study_snapshot(study)
        deleted_study = self.get_delete_study_service().execute(
            DeleteStudyCommand(
                study_id=study.pk,
                actor_user_id=request.user.pk,
            )
        )
        self.get_study_audit_service().record_deleted(
            request=request,
            study=deleted_study,
            before_data=before_data,
        )
        return redirect(reverse("study:study_list"))
