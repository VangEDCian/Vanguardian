import datetime

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.shared.views.generic import AuthenticateTemplateView
from apps.study.application import (
    CreateStudyCommand,
    CreateStudyService,
    StudyCodeAlreadyExistsError,
    StudyDateRangeError,
    StudyDirectoryQueryService,
    StudyFilterActiveQueryService,
    StudyFilterInactiveQueryService,
    StudyNotFoundError,
    UpdateStudyCommand,
    UpdateStudyService,
)
from apps.study.infrastructure.persistence.models import Study
from apps.study.presentation.web.forms import StudyForm


class StudyListView(LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView):
    permission_required = "study.view_study_list"
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
        context.update(
            self.get_study_directory_query_service().list_studies(
                search_query=self.request.GET.get("q", ""),
                filter_key=self.request.GET.get("filter", ""),
                sort_key=self.request.GET.get("sort", "code"),
                sort_direction=self.request.GET.get("direction", "asc"),
            )
        )
        return context


class StudyDetailView(LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView):
    permission_required = "study.view_study_detail"
    template_name = "study/study_detail.html"
    layout_nav_key = "STUDIES"
    study_directory_query_service_class = StudyDirectoryQueryService
    _detail_view_model = None

    def get_study_directory_query_service(self):
        return self.study_directory_query_service_class()

    def dispatch(self, request, *args, **kwargs):
        try:
            self._detail_view_model = self.get_study_directory_query_service().get_study_detail(
                study_id=kwargs["study_id"]
            )
        except StudyNotFoundError as exc:
            raise Http404 from exc
        return super().dispatch(request, *args, **kwargs)

    def get_layout_breadcrumb_label(self):
        if self._detail_view_model is None:
            return super().get_layout_breadcrumb_label()
        return self._detail_view_model["layout_breadcrumb_label"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self._detail_view_model is not None:
            context["detail_study"] = self._detail_view_model["detail_study"]
        context["active_tab"] = self.request.GET.get("tab", "info")
        return context


class StudyCreateView(LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView):
    permission_required = "study.create_study"
    template_name = "study/study_form.html"
    layout_nav_key = "STUDIES"
    layout_breadcrumb_label = _("NEW STUDY")
    create_study_service_class = CreateStudyService

    def get_create_study_service(self):
        return self.create_study_service_class()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("form", StudyForm())
        context["form_action"] = reverse("study:study_create")
        context["form_title"] = _("New Study")
        context["back_url"] = reverse("study:study_list")
        context["start_date_min"] = datetime.date.today().strftime("%Y-%m-%d")
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

        return redirect(reverse("study:study_detail", kwargs={"study_id": study.pk}))

    def _render_form(self, request, form):
        context = self.get_context_data(form=form)
        return self.render_to_response(context)


class StudyUpdateView(LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView):
    permission_required = "study.update_study"
    template_name = "study/study_form.html"
    layout_nav_key = "STUDIES"
    update_study_service_class = UpdateStudyService
    _study = None

    def dispatch(self, request, *args, **kwargs):
        self._study = Study.objects.filter(pk=kwargs["study_id"], deleted=False).first()
        if self._study is None:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_layout_breadcrumb_label(self):
        if self._study is None:
            return super().get_layout_breadcrumb_label()
        return self._study.code

    def get_update_study_service(self):
        return self.update_study_service_class()

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
        context["form_action"] = reverse("study:study_update", kwargs={"study_id": self._study.pk})
        context["form_title"] = self._study.code
        context["back_url"] = reverse("study:study_detail", kwargs={"study_id": self._study.pk})
        return context

    def post(self, request, *args, **kwargs):
        form = StudyForm(request.POST)
        if not form.is_valid():
            return self._render_form(request, form)

        command = UpdateStudyCommand(
            study_id=self._study.pk,
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
            self.get_update_study_service().execute(command)
        except StudyCodeAlreadyExistsError:
            form.add_error("code", _("This study code already exists."))
            return self._render_form(request, form)
        except StudyDateRangeError:
            form.add_error("end_date", _("End date must be on or after start date."))
            return self._render_form(request, form)

        return redirect(reverse("study:study_detail", kwargs={"study_id": self._study.pk}))

    def _render_form(self, request, form):
        context = self.get_context_data(form=form)
        return self.render_to_response(context)
