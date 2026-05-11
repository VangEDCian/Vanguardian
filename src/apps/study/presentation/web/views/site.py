from django.contrib.auth.decorators import permission_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
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
from apps.study.infrastructure.repositories import DjangoStudyCommandRepository
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
        return (
            super().get_queryset()
            .select_related("investigator")
            .filter(study_id=self.get_study_id(), deleted=False)
        )

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


class SiteInvestigatorContextMixin:
    command_repository_class = DjangoStudyCommandRepository

    def get_command_repository(self):
        return self.command_repository_class()

    @staticmethod
    def _build_user_option(user, *, selected):
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        if full_name:
            text = f"{full_name} ({user.username})"
        elif user.display_name:
            text = f"{user.display_name} ({user.username})"
        else:
            text = user.username
        return {
            "value": str(user.pk),
            "label": text,
            "selected": selected,
        }

    def _build_investigator_options(self, *, study_id, site_id, selected_user_id):
        repository = self.get_command_repository()
        users = repository.list_users_for_study_or_site_membership(
            study_id=study_id,
            site_id=site_id,
        )[:100]

        selected_id_str = str(selected_user_id) if selected_user_id else None
        options = [
            self._build_user_option(user, selected=str(user.pk) == selected_id_str)
            for user in users
        ]

        if selected_id_str and not any(option["value"] == selected_id_str for option in options):
            selected_user = repository.get_user(user_id=selected_user_id)
            if selected_user is not None:
                options.append(self._build_user_option(selected_user, selected=True))

        return options


class SiteDetailView(
    SiteInvestigatorContextMixin,
    AuthenticateTemplateContextMixin,
    DetailView,
    SiteAbstractVerifyStudy,
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
                    "investigator": self.object.investigator_id or "",
                    "study_id": str(self.object.study_id),
                    "is_active": self.object.is_active,
                },
            )

        context["site"] = self.object
        context["form"] = form
        context["study_options"] = StudySiteDirectoryQueryService.build_site_study_options(
            studies, self.object.study_id,
        )
        context["investigator_options"] = self._build_investigator_options(
            study_id=self.object.study_id,
            site_id=self.object.pk,
            selected_user_id=form["investigator"].value() or self.object.investigator_id,
        )
        context["memberships_api_url"] = reverse(
            "study:api_site_memberships",
            kwargs={"study_id": self.object.study_id, "site_id": self.object.pk},
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
                investigator_id=form.cleaned_data.get("investigator"),
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


class SiteCreateView(SiteInvestigatorContextMixin, AuthenticateTemplateView, SiteAbstractVerifyStudy):
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
        context["investigator_options"] = self._build_investigator_options(
            study_id=selected_study_id,
            site_id=0,
            selected_user_id=form["investigator"].value(),
        )
        context["memberships_api_url"] = reverse(
            "study:api_site_memberships",
            kwargs={"study_id": selected_study_id, "site_id": 0},
        )
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
                    investigator_id=form.cleaned_data.get("investigator"),
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


class SiteMembershipOptionsApiView(SiteInvestigatorContextMixin, AuthenticateTemplateContextMixin, View):
    @staticmethod
    def _normalize_id(value):
        normalized = str(value).strip()
        return int(normalized) if normalized.isdigit() else None

    def get(self, request, *args, **kwargs):
        study_id = self._normalize_id(kwargs.get("study_id"))
        site_id = self._normalize_id(kwargs.get("site_id"))
        if study_id is None or site_id is None:
            raise Http404

        search_query = (request.GET.get("q") or "").strip()
        users = self.get_command_repository().list_users_for_study_or_site_membership(
            study_id=study_id,
            site_id=site_id,
            search_query=search_query,
        )[:100]

        return JsonResponse(
            {
                "results": [
                    {
                        "id": str(user.pk),
                        "text": self._build_user_option(user, selected=False)["label"],
                    }
                    for user in users
                ],
            },
        )
