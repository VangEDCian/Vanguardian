from django.contrib.auth.decorators import permission_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, ListView
from django_filters.views import FilterView
from django_tables2 import SingleTableMixin

from apps.audit.public import build_audit_request_context
from apps.shared.context_processors import StudyDropdownHandler
from apps.shared.views import AuthenticateTemplateContextMixin, AuthenticateTemplateView
from apps.study.application.commands.site_data import (
    CreateSiteCommand,
    DeleteSiteCommand,
    SiteCodeAlreadyExistsError,
    SiteNotFoundError,
    UpdateSiteCommand,
)
from apps.study.application.services import (
    CreateSiteService,
    DeleteSiteService,
    StudySiteDirectoryQueryService,
    UpdateSiteService,
)
from apps.study.application.services.site_audit import SiteAuditService
from apps.study.infrastructure.persistence.models import Site, Study
from apps.study.presentation.web.forms.site import SiteForm, SitesToolbarForm
from apps.study.presentation.web.tables import SiteListTable
from apps.study.presentation.web.views.helpers import _user_has_study_access


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
    AuthenticateTemplateContextMixin,
    SingleTableMixin, FilterView, ListView,
    SiteAbstractVerifyStudy,
):
    permission_required = "site.view_site_list"
    raise_exception = True
    layout_nav_key = "SITES"
    layout_breadcrumb_label = _("SITES")

    model = Site
    template_name = "study/sites.html"
    table_class = SiteListTable
    filterset_class = SitesToolbarForm
    paginate_by = 10

    study_obj: Study = None

    def get_queryset(self):
        return super().get_queryset().filter(study_id=self.get_study_id(), deleted=False)

    @staticmethod
    def _get_resolved_study_id(request):
        return StudyDropdownHandler(request=request).build().selected_id

    def get(self, request, *args, **kwargs):
        path_study_id = self.get_study_id()
        resolved_study_id = self._get_resolved_study_id(request)
        if path_study_id and resolved_study_id:
            if path_study_id == resolved_study_id:
                return super().get(request, *args, **kwargs)
            return redirect(reverse("study:site_list", kwargs={'study_id': resolved_study_id}))
        return redirect(reverse('dashboard:main'))


class SiteDetailView(
    AuthenticateTemplateContextMixin, DetailView, SiteAbstractVerifyStudy,
):
    layout_nav_key = "SITES"
    layout_breadcrumb_label = _("SITES")
    template_name = "study/site_detail.html"

    pk_url_kwarg = 'site_id'
    model = Site

    def get_queryset(self):
        return super().get_queryset().filter(study_id=self.get_study_id(), deleted=False)

    def get_layout_breadcrumb_label(self):
        return super().get_layout_breadcrumb_label()

    def get_layout_show_breadcrumb_trail(self):
        return False

    def get_layout_detail_meta_items(self):
        if not getattr(self, "object", None):
            return super().get_layout_detail_meta_items()
        return (
            {
                "label": _("Site Code"),
                "value": self.object.code,
            },
            {
                "value": _("Active") if self.object.is_active else _("Inactive"),
            },
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        studies = StudySiteDirectoryQueryService.get_active_studies(self.request.user)
        choices = StudySiteDirectoryQueryService.study_choices(studies)

        form = kwargs.get("form")
        if form is None:
            form = SiteForm(
                study_choices=choices,
                fixed_code=self.object.code,
                fixed_study_id=self.object.study_id,
                initial={
                    "code": self.object.code,
                    "name": self.object.name,
                    "investigator": self.object.investigator or "",
                    "study_id": str(self.object.study_id),
                    "is_active": self.object.is_active,
                },
            )

        context["site"] = self.object
        context["form"] = form
        context["study_options"] = StudySiteDirectoryQueryService.build_site_study_options(
            studies, self.object.study_id,
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
            fixed_code=site.code,
            fixed_study_id=site.study_id,
        )

        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        # snapshot before change
        snapshot_before_data = StudySiteDirectoryQueryService.snapshot_site_obj(site=site)

        UpdateSiteService().execute(
            UpdateSiteCommand(
                site_id=site.pk,
                name=form.cleaned_data["name"],
                investigator=form.cleaned_data.get("investigator") or "",
                is_active=form.cleaned_data.get("is_active", False),
                actor_user_id=request.user.pk,
            ),
        )

        # snapshot after change
        SiteAuditService().record_updated(
            object_id=site.id,
            before_data=snapshot_before_data,
            after_data=StudySiteDirectoryQueryService.snapshot_site_obj(site=site),
            **build_audit_request_context(request),
        )

        return redirect(
            reverse(
                "study:site_detail", kwargs={"site_id": site.pk, 'study_id': self.get_study_id()},
            ),
        )


class SiteCreateView(AuthenticateTemplateView, SiteAbstractVerifyStudy):
    layout_nav_key = "SITES"
    layout_breadcrumb_label = _("NEW SITE")
    template_name = "study/site_create.html"

    def _get_studies(self):
        return StudySiteDirectoryQueryService.get_active_studies(
            self.request.user,
        )

    def _get_selected_study_id(self):
        selected_study_id = StudyDropdownHandler(request=self.request).build().selected_id
        if selected_study_id is not None:
            return selected_study_id
        return self.get_study_id()

    def _get_selected_study(self):
        selected_study_id = self._get_selected_study_id()
        if selected_study_id is None:
            return None
        return self._get_studies().filter(pk=selected_study_id).first()

    def dispatch(self, request, *args, **kwargs):
        selected_study_id = self._get_selected_study_id()
        if selected_study_id is None:
            raise Http404
        if not _user_has_study_access(request.user, selected_study_id):
            raise PermissionDenied
        if self._get_selected_study() is None:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_study_id = self._get_selected_study_id()

        form = kwargs.get("form")
        if form is None:
            form = SiteForm(fixed_study_id=selected_study_id)

        context["form"] = form
        context["back_url"] = reverse("study:site_list", kwargs={'study_id': selected_study_id})
        context["create_url"] = reverse(
            "study:site_create", kwargs={'study_id': selected_study_id},
        )
        return context

    @method_decorator(permission_required('site.create_site', raise_exception=True))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @method_decorator(permission_required('site.create_site', raise_exception=True))
    def post(self, request, *args, **kwargs):
        selected_study_id = self._get_selected_study_id()
        if selected_study_id is None:
            raise Http404
        if self._get_selected_study() is None:
            raise Http404

        form = SiteForm(
            request.POST,
            fixed_study_id=selected_study_id,
        )

        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        try:
            site = CreateSiteService().execute(
                CreateSiteCommand(
                    code=form.cleaned_data["code"],
                    name=form.cleaned_data["name"],
                    investigator=form.cleaned_data.get("investigator") or "",
                    study_id=selected_study_id,
                    is_active=form.cleaned_data.get("is_active", True),
                    actor_user_id=request.user.pk,
                ),
            )
        except SiteCodeAlreadyExistsError:
            form.add_error("code", _("This site code already exists in the current study."))
            return self.render_to_response(self.get_context_data(form=form))

        SiteAuditService().record_created(
            object_id=site.id,
            after_data=StudySiteDirectoryQueryService.snapshot_site_obj(site),
            **build_audit_request_context(request),
        )

        return redirect(
            reverse(
                "study:site_detail", kwargs={"site_id": site.pk, 'study_id': selected_study_id},
            ),
        )


class SiteDeleteView(AuthenticateTemplateContextMixin, DetailView, SiteAbstractVerifyStudy):
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
        SiteAuditService().record_deleted(
            object_id=site.id,
            before_data=snapshot_before_data,
            **build_audit_request_context(request),
        )

        return redirect(reverse("study:site_list", kwargs={'study_id': self.get_study_id()}))
