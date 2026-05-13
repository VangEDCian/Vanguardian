from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.audit.public import build_audit_request_context
from apps.shared.views import AuthenticateTemplateView
from apps.study.application import (
    StudyAuditService,
    StudyCodeAlreadyExistsError,
    StudyDateRangeError,
    StudyDirectoryQueryService,
    StudyFilterActiveQueryService,
    StudyFilterInactiveQueryService,
    StudyNotFoundError,
    UpdateStudyService,
)
from apps.study.infrastructure.persistence.models import Study
from apps.study.presentation.web.forms import StudyForm
from apps.study.presentation.web.mappers.commands import to_update_study_command
from apps.study.presentation.web.views.helpers import (
    _can_change_study_status,
    _serialize_study_snapshot,
    _user_has_study_access,
)


class StudyListView(
    AuthenticateTemplateView
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
    AuthenticateTemplateView
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

        command = to_update_study_command(
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
            study=updated_study,
            before_data=before_data,
            **build_audit_request_context(request),
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
