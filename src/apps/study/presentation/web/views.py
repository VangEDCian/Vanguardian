import datetime

from django.contrib.auth.decorators import permission_required
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import ListView, DetailView

from django_filters.views import FilterView

from django_tables2 import SingleTableMixin

from apps.identity.infrastructure.persistence.models import StudyMembership

from apps.shared.views.generic import AuthenticateTemplateView
from apps.shared.views.generic.authenticate_template_view import AuthenticateTemplateContextMixin

from apps.study.application import (
    CreateStudyCommand,
    CreateStudyService,
    DeleteStudyCommand,
    DeleteStudyService,
    StudyAuditService,
    StudyCrfTemplateDirectoryQueryService,
    StudyEventDefinitionDirectoryQueryService,
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
from apps.study.application.services.site_audit import SiteAuditService
from apps.study.infrastructure.persistence.models import Study
from apps.study.presentation.web.forms import StudyForm, SiteForm
from apps.study.presentation.web.tables import SiteListTable
from apps.study.application.queries.site_filter import SitesFilter
from apps.study.infrastructure.persistence.models import Site
from apps.study.application.commands.site import (
    CreateSiteService,
    UpdateSiteService,
    DeleteSiteService,
)
from apps.study.application.commands.site_data import (
    CreateSiteCommand,
    UpdateSiteCommand,
    DeleteSiteCommand,
    SiteCodeAlreadyExistsError,
    SiteNotFoundError,
)
from apps.study.application.queries.site_directory import StudySiteDirectoryQueryService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_has_study_access(user, study_id):
    """Return True if the user is allowed to access the given study.

    Django superusers bypass scope filtering and can access all studies.
    All other users must have an active, non-deleted StudyMembership for the study.
    """
    if user.is_superuser:
        return True
    return StudyMembership.objects.filter(user=user, study_id=study_id, deleted=False).exists()


def _can_change_study_status(user):
    return user.has_perm("study.change_study_status")


def _serialize_study_snapshot(study):
    return {
        "code": study.code,
        "name": study.name,
        "sponsor": study.sponsor,
        "description": study.description,
        "start_date": study.start_date.isoformat() if study.start_date else None,
        "end_date": study.end_date.isoformat() if study.end_date else None,
        "is_active": study.is_active,
    }


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

class StudyListView(LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView):
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
                filter_key=self.request.GET.get("filter", "") if can_filter_status else "",
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


class StudyDetailView(LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView):
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
        study_id = self._detail_view_model["detail_study"]["id"]

        user = self.request.user
        can_toggle_status = _can_change_study_status(user)
        can_update_field_name = user.has_perm("study.update_study_field_name")
        can_update_field_sponsor = user.has_perm("study.update_study_field_sponsor")
        can_update_field_dates = user.has_perm("study.update_study_field_dates")
        can_update_field_description = user.has_perm("study.update_study_field_description")
        can_update_detail = any(
            (
                can_update_field_name,
                can_update_field_sponsor,
                can_update_field_dates,
                can_update_field_description,
                can_toggle_status,
            )
        )

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
        context["delete_url"] = reverse("study:study_delete", kwargs={"study_id": study_id})

        # Field-level view permissions
        context["can_view_field_code"] = user.has_perm("study.view_study_field_code")
        context["can_view_field_name"] = user.has_perm("study.view_study_field_name")
        context["can_view_field_sponsor"] = user.has_perm("study.view_study_field_sponsor")
        context["can_view_field_dates"] = user.has_perm("study.view_study_field_dates")
        context["can_view_field_description"] = user.has_perm("study.view_study_field_description")
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
            name=form.cleaned_data["name"] if request.user.has_perm("study.update_study_field_name") else self._study.name,
            sponsor=form.cleaned_data["sponsor"] if request.user.has_perm("study.update_study_field_sponsor") else self._study.sponsor,
            description=form.cleaned_data["description"] if request.user.has_perm("study.update_study_field_description") else self._study.description,
            start_date=form.cleaned_data.get("start_date") if request.user.has_perm("study.update_study_field_dates") else self._study.start_date,
            end_date=form.cleaned_data.get("end_date") if request.user.has_perm("study.update_study_field_dates") else self._study.end_date,
            is_active=form.cleaned_data.get("is_active", False) if _can_change_study_status(request.user) else self._study.is_active,
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

        return redirect(reverse("study:study_detail", kwargs={"study_id": self._study.pk}))

    def _can_update_detail(self, request_user):
        return any(
            (
                request_user.has_perm("study.update_study_field_name"),
                request_user.has_perm("study.update_study_field_sponsor"),
                request_user.has_perm("study.update_study_field_dates"),
                request_user.has_perm("study.update_study_field_description"),
                _can_change_study_status(request_user),
            )
        )


class StudyCrfTemplateListView(LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView):
    permission_required = "study.view_study_detail"
    raise_exception = True
    template_name = "study/crf_templates.html"
    layout_nav_key = "STUDIES"
    study_directory_query_service_class = StudyDirectoryQueryService
    study_crf_template_directory_query_service_class = StudyCrfTemplateDirectoryQueryService
    _detail_view_model = None
    _study = None

    def get_study_directory_query_service(self):
        return self.study_directory_query_service_class()

    def get_study_crf_template_directory_query_service(self):
        return self.study_crf_template_directory_query_service_class()

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
            self.get_study_crf_template_directory_query_service().list_crf_templates(
                study_id=self._study.pk,
                search_query=self.request.GET.get("q", ""),
                sort_key=self.request.GET.get("sort", "code"),
                sort_direction=self.request.GET.get("direction", "asc"),
            )
        )
        return context


class StudyEventDefinitionListView(LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView):
    permission_required = "study.view_study_detail"
    raise_exception = True
    template_name = "study/event_definitions.html"
    layout_nav_key = "STUDIES"
    study_directory_query_service_class = StudyDirectoryQueryService
    study_event_definition_directory_query_service_class = StudyEventDefinitionDirectoryQueryService
    _detail_view_model = None
    _study = None

    def get_study_directory_query_service(self):
        return self.study_directory_query_service_class()

    def get_study_event_definition_directory_query_service(self):
        return self.study_event_definition_directory_query_service_class()

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
        return context


class StudyCreateView(LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView):
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


class StudyUpdateView(LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView):
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
        context.setdefault("form", StudyForm(initial={
            "code": self._study.code,
            "name": self._study.name,
            "sponsor": self._study.sponsor,
            "description": self._study.description,
            "start_date": self._study.start_date,
            "end_date": self._study.end_date,
            "is_active": self._study.is_active,
        }))
        user = self.request.user
        context["form_action"] = reverse("study:study_update", kwargs={"study_id": self._study.pk})
        context["form_title"] = self._study.code
        context["back_url"] = reverse("study:study_detail", kwargs={"study_id": self._study.pk})
        context["can_edit_code"] = user.has_perm("study.update_study_field_code")
        context["show_is_active"] = False

        # Field-level update permissions
        context["can_update_field_code"] = user.has_perm("study.update_study_field_code")
        context["can_update_field_name"] = user.has_perm("study.update_study_field_name")
        context["can_update_field_sponsor"] = user.has_perm("study.update_study_field_sponsor")
        context["can_update_field_dates"] = user.has_perm("study.update_study_field_dates")
        context["can_update_field_description"] = user.has_perm("study.update_study_field_description")
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

        return redirect(reverse("study:study_detail", kwargs={"study_id": self._study.pk}))

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

        self.get_study_audit_service().record_status_changed(request=request, study=study)

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


#
# Site
#
class SiteAbstractVerifyStudy(View):
    study_obj: Study | None = None

    def get_study_id(self):
        return self.kwargs["study_id"]

    def dispatch(self, request, *args, **kwargs):
        study_id = self.get_study_id()
        self.study_obj = StudySiteDirectoryQueryService.get_study_id(study_id=study_id)
        if self.study_obj:
            return super().dispatch(request, *args, **kwargs)
        raise Http404


class SiteListView(
    LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateContextMixin,
    SingleTableMixin, FilterView, ListView,
    SiteAbstractVerifyStudy,
):
    permission_required = "site.view_site_list"
    raise_exception = True
    layout_nav_key = "SITES"
    layout_breadcrumb_label = _("SITES")

    model = Site
    template_name = "study/site_list.html"
    table_class = SiteListTable
    filterset_class = SitesFilter
    paginate_by = 10

    study_obj: Study = None

    def get_queryset(self):
        return super().get_queryset().filter(study_id=self.get_study_id(), deleted=False)


class SiteDetailView(
    LoginRequiredMixin, AuthenticateTemplateContextMixin, DetailView, SiteAbstractVerifyStudy,
):
    layout_nav_key = "SITES"
    layout_breadcrumb_label = _("SITES")
    template_name = "study/site_detail.html"

    pk_url_kwarg = 'site_id'
    model = Site

    def get_queryset(self):
        return super().get_queryset().filter(study_id=self.get_study_id(), deleted=False)

    def get_layout_breadcrumb_label(self):
        if self.object:
            return self.object.code
        return super().get_layout_breadcrumb_label()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        studies = StudySiteDirectoryQueryService.get_active_studies(self.request.user)
        choices = StudySiteDirectoryQueryService.study_choices(studies)

        form = kwargs.get("form")
        if form is None:
            form = SiteForm(
                study_choices=choices,
                initial={
                    "code": self.object.code,
                    "name": self.object.name,
                    "investigator": self.object.investigator or "",
                    "study_id": str(self.object.study_id),
                    "is_active": self.object.is_active,
                },
            )

        selected_id = form.data.get("study_id") if form.is_bound else self.object.study_id

        context["site"] = self.object
        context["form"] = form
        context["study_options"] = StudySiteDirectoryQueryService.build_site_study_options(
            studies, selected_id,
        )
        context["back_url"] = reverse("study:site_list", kwargs={'study_id': self.get_study_id()})
        context["update_url"] = reverse(
            "study:site_detail",
            kwargs={"site_id": self.object.pk, 'study_id': self.get_study_id()},
        )
        context["delete_url"] = reverse(
            "study:site_delete",
            kwargs={"site_id": self.object.pk, 'study_id': self.get_study_id()},
        )
        context["can_update_site"] = self.request.user.has_perm("site.update_site")
        context["can_delete_site"] = self.request.user.has_perm("site.delete_site")
        return context

    def get_object(self, *args, **kwargs):
        instance: Site | None = super().get_object(*args, **kwargs)
        if instance and instance.deleted is False:
            return instance
        raise Http404

    @method_decorator(permission_required('site.view_site_detail', raise_exception=True))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @method_decorator(permission_required('site.view_site_detail', raise_exception=True))
    def post(self, request, *args, **kwargs):
        if not request.user.has_perm("site.update_site"):
            raise PermissionDenied

        site = self.get_object()
        studies = StudySiteDirectoryQueryService.get_active_studies(
            request.user,
        )
        form = SiteForm(
            request.POST,
            study_choices=StudySiteDirectoryQueryService.study_choices(
                studies,
            ),
        )

        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        # snapshot before change
        snapshot_before_data = StudySiteDirectoryQueryService.snapshot_site_obj(site=site)

        try:
            UpdateSiteService().execute(
                UpdateSiteCommand(
                    site_id=site.pk,
                    code=form.cleaned_data["code"],
                    name=form.cleaned_data["name"],
                    investigator=form.cleaned_data.get("investigator") or "",
                    study_id=form.cleaned_data["study_id"],
                    is_active=form.cleaned_data.get("is_active", False),
                    actor_user_id=request.user.pk,
                ),
            )
        except SiteCodeAlreadyExistsError:
            form.add_error("code", _("This site code already exists in the selected study."))
            return self.render_to_response(self.get_context_data(form=form))

        # snapshot after change
        SiteAuditService(request=request).record_updated(
            object_id=site.id,
            before_data=snapshot_before_data,
            after_data=StudySiteDirectoryQueryService.snapshot_site_obj(site=site),
        )

        return redirect(
            reverse(
                "study:site_detail", kwargs={"site_id": site.pk, 'study_id': self.get_study_id()},
            ),
        )


class SiteCreateView(LoginRequiredMixin, AuthenticateTemplateView, SiteAbstractVerifyStudy):
    layout_nav_key = "SITES"
    layout_breadcrumb_label = _("NEW SITE")
    template_name = "study/site_create.html"

    def _get_studies(self):
        return StudySiteDirectoryQueryService.get_active_studies(
            self.request.user,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        studies = self._get_studies()
        choices = StudySiteDirectoryQueryService.study_choices(studies)

        form = kwargs.get("form")
        if form is None:
            form = SiteForm(study_choices=choices)

        selected_id = form.data.get("study_id") if form.is_bound else None

        context["form"] = form
        context["study_options"] = StudySiteDirectoryQueryService.build_site_study_options(
            studies, selected_id,
        )
        context["back_url"] = reverse("study:site_list", kwargs={'study_id': self.get_study_id()})
        context["create_url"] = reverse(
            "study:site_create", kwargs={'study_id': self.get_study_id()},
        )
        return context

    @method_decorator(permission_required('site.create_site', raise_exception=True))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @method_decorator(permission_required('site.create_site', raise_exception=True))
    def post(self, request, *args, **kwargs):
        studies = self._get_studies()
        form = SiteForm(
            request.POST,
            study_choices=StudySiteDirectoryQueryService.study_choices(
                studies,
            ),
        )

        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        try:
            site = CreateSiteService().execute(
                CreateSiteCommand(
                    code=form.cleaned_data["code"],
                    name=form.cleaned_data["name"],
                    investigator=form.cleaned_data.get("investigator") or "",
                    study_id=form.cleaned_data["study_id"],
                    is_active=form.cleaned_data.get("is_active", True),
                    actor_user_id=request.user.pk,
                ),
            )
        except SiteCodeAlreadyExistsError:
            form.add_error("code", _("This site code already exists in the selected study."))
            return self.render_to_response(self.get_context_data(form=form))

        SiteAuditService(request=request).record_created(
            object_id=site.id,
            after_data=StudySiteDirectoryQueryService.snapshot_site_obj(site),
        )

        return redirect(
            reverse(
                "study:site_detail", kwargs={"site_id": site.pk, 'study_id': self.get_study_id()},
            ),
        )


class SiteDeleteView(LoginRequiredMixin, DetailView, SiteAbstractVerifyStudy):
    pk_url_kwarg = 'site_id'
    model = Site

    def get_queryset(self):
        return super().get_queryset().filter(study_id=self.get_study_id(), deleted=False)

    @method_decorator(permission_required('site.delete_site', raise_exception=True))
    def post(self, request, *args, **kwargs):
        site: Site | None = self.get_object()
        if not site:
            raise Http404
        if not _user_has_study_access(request.user, self.get_study_id()):
            raise PermissionDenied

        # snapshot before destroy
        snapshot_before_data = StudySiteDirectoryQueryService.snapshot_site_obj(site=site)

        try:
            DeleteSiteService().execute(
                DeleteSiteCommand(site_id=site.pk, actor_user_id=request.user.pk),
            )
        except SiteNotFoundError:
            raise Http404

        # snapshot after change
        SiteAuditService(request=request).record_deleted(
            object_id=site.id,
            before_data=snapshot_before_data,
        )

        return redirect(reverse("study:site_list", kwargs={'study_id': self.get_study_id()}))
