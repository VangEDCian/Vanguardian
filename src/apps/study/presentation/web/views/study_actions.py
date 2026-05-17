import datetime

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View

from apps.audit.public import build_audit_request_context
from apps.shared.views import AuthenticateTemplateContextMixin, AuthenticateTemplateView
from apps.study.application import (
    CreateStudyService,
    DeleteStudyService,
    StudyAuditService,
    StudyCodeAlreadyExistsError,
    StudyDateRangeError,
    StudyNotFoundError,
    ToggleStudyStatusService,
    UpdateStudyService,
)
from apps.study.infrastructure.persistence.models import Study
from apps.study.presentation.web.forms import StudyForm
from apps.study.presentation.web.mappers.commands import (
    to_create_study_command,
    to_delete_study_command,
    to_toggle_study_status_command,
    to_update_study_command,
)
from apps.study.presentation.web.views.helpers import (
    _serialize_study_snapshot,
    _user_has_study_access,
)


class StudyCreateView(
    AuthenticateTemplateView
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

        command = to_create_study_command(
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

        self.get_study_audit_service().record_created(
            study=study,
            **build_audit_request_context(request),
        )

        return redirect(reverse("study:study_detail", kwargs={"study_id": study.pk}))

    def _render_form(self, request, form):
        context = self.get_context_data(form=form)
        return self.render_to_response(context)


class StudyUpdateView(
    AuthenticateTemplateView
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

        command = to_update_study_command(
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
            study=updated_study,
            before_data=before_data,
            **build_audit_request_context(request),
        )

        return redirect(
            reverse("study:study_detail", kwargs={"study_id": self._study.pk})
        )

    def _render_form(self, request, form):
        context = self.get_context_data(form=form)
        return self.render_to_response(context)


class StudyToggleStatusView(AuthenticateTemplateContextMixin, View):
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
        command = to_toggle_study_status_command(
            study_id=study_id,
            actor_user_id=request.user.pk,
        )

        try:
            study = self.get_toggle_study_status_service().execute(command)
        except StudyNotFoundError:
            raise Http404

        self.get_study_audit_service().record_status_changed(
            study=study,
            **build_audit_request_context(request),
        )

        return redirect(reverse("study:study_detail", kwargs={"study_id": study_id}))


class StudyDeleteView(AuthenticateTemplateContextMixin, View):
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
            to_delete_study_command(
                study_id=study.pk,
                actor_user_id=request.user.pk,
            )
        )
        self.get_study_audit_service().record_deleted(
            study=deleted_study,
            before_data=before_data,
            **build_audit_request_context(request),
        )
        return redirect(reverse("study:study_list"))
