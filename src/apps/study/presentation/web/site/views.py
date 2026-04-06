from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View

from django_tables2.views import SingleTableMixin
from django_filters.views import FilterView
from django.views.generic import ListView

from apps.identity.infrastructure.persistence.models import StudyMembership, User
from apps.shared.views import AuthenticateTemplateContextMixin, AuthenticateTemplateView

from apps.study.application.commands.site import (
    CreateSiteCommand,
    CreateSiteMembershipCommand,
    CreateSiteMembershipService,
    CreateSiteService,
    DeleteSiteCommand,
    DeleteSiteMembershipCommand,
    DeleteSiteMembershipService,
    DeleteSiteService,
    SiteCodeAlreadyExistsError,
    SiteMembershipAlreadyExistsError,
    SiteMembershipNotFoundError,
    UpdateSiteCommand,
    UpdateSiteService,
)
from apps.study.application.queries.site import (
    SiteDirectoryQueryService, SiteMembershipQueryService, SiteNotFoundError,
)
from apps.study.models import Site
from apps.study.presentation.web.site.filters import SitesFilter
from apps.study.presentation.web.site.forms import SiteForm, SiteMembershipForm
from apps.study.infrastructure.persistence.models import Study
from apps.study.presentation.web.site.tables import SiteListTable


def _user_has_study_access(user, study_id):
    if user.is_superuser:
        return True
    return StudyMembership.objects.filter(user=user, study_id=study_id, deleted=False).exists()


class SiteListView(
    LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateContextMixin,
    SingleTableMixin, FilterView, ListView,
):
    permission_required = "site.view_site_list"
    raise_exception = True
    layout_nav_key = "SITES"
    layout_breadcrumb_label = _("SITES")

    model = Site
    template_name = "study/site/sites.html"
    table_class = SiteListTable
    filterset_class = SitesFilter
    paginate_by = 2


class SiteCreateView(LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView):
    permission_required = "site.create_site"
    raise_exception = True
    template_name = "study/site/site_form.html"
    layout_nav_key = "SITES"
    layout_breadcrumb_label = _("NEW SITE")
    create_site_service_class = CreateSiteService

    def get_create_site_service(self):
        return self.create_site_service_class()

    def get_study_choices(self, user):
        queryset = Study.objects.filter(deleted=False).order_by("code")
        if not user.is_superuser:
            member_study_ids = StudyMembership.objects.filter(user=user, deleted=False).values_list(
                "study_id", flat=True,
            )
            queryset = queryset.filter(pk__in=member_study_ids)
        return [(study.pk, f"{study.code} - {study.name}") for study in queryset]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault(
            "form", SiteForm(study_choices=self.get_study_choices(self.request.user)),
        )
        context["form_title"] = _("New Site")
        context["back_url"] = reverse("study:site_list")
        return context

    def post(self, request, *args, **kwargs):
        form = SiteForm(request.POST, study_choices=self.get_study_choices(request.user))
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        if not _user_has_study_access(request.user, form.cleaned_data["study_id"]):
            raise PermissionDenied

        command = CreateSiteCommand(
            code=form.cleaned_data["code"],
            name=form.cleaned_data["name"],
            investigator=form.cleaned_data["investigator"],
            study_id=form.cleaned_data["study_id"],
            is_active=form.cleaned_data.get("is_active", True),
            actor_user_id=request.user.pk,
        )

        try:
            site = self.get_create_site_service().execute(command)
        except SiteCodeAlreadyExistsError:
            form.add_error("code", _("This site code already exists in the selected study."))
            return self.render_to_response(self.get_context_data(form=form))

        return redirect(reverse("study:site_detail", kwargs={"site_id": site.pk}))


class SiteDetailView(LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView):
    permission_required = "site.view_site_detail"
    raise_exception = True
    template_name = "study/site/site_detail.html"
    layout_nav_key = "SITES"
    site_directory_query_service_class = SiteDirectoryQueryService
    _site = None

    def get_site_directory_query_service(self):
        return self.site_directory_query_service_class()

    def dispatch(self, request, *args, **kwargs):
        try:
            self._site = self.get_site_directory_query_service().get_site_detail(
                site_id=kwargs["site_id"],
                user=request.user,
            )
        except SiteNotFoundError as exc:
            raise Http404 from exc
        return super().dispatch(request, *args, **kwargs)

    def get_layout_breadcrumb_label(self):
        if self._site is None:
            return super().get_layout_breadcrumb_label()
        return self._site.code

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["site"] = self._site
        context["edit_url"] = reverse("study:site_update", kwargs={"site_id": self._site.pk})
        context["back_url"] = reverse("study:site_list")
        context["delete_url"] = reverse("study:site_delete", kwargs={"site_id": self._site.pk})
        return context


class SiteUpdateView(LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView):
    permission_required = "site.update_site"
    raise_exception = True
    template_name = "study/site/site_form.html"
    layout_nav_key = "SITES"
    update_site_service_class = UpdateSiteService
    site_directory_query_service_class = SiteDirectoryQueryService
    _site = None

    def get_update_site_service(self):
        return self.update_site_service_class()

    def get_site_directory_query_service(self):
        return self.site_directory_query_service_class()

    def get_study_choices(self, user):
        queryset = Study.objects.filter(deleted=False).order_by("code")
        if not user.is_superuser:
            member_study_ids = StudyMembership.objects.filter(user=user, deleted=False).values_list(
                "study_id", flat=True,
            )
            queryset = queryset.filter(pk__in=member_study_ids)
        return [(study.pk, f"{study.code} - {study.name}") for study in queryset]

    def dispatch(self, request, *args, **kwargs):
        try:
            self._site = self.get_site_directory_query_service().get_site_detail(
                site_id=kwargs["site_id"],
                user=request.user,
            )
        except SiteNotFoundError as exc:
            raise Http404 from exc
        return super().dispatch(request, *args, **kwargs)

    def get_layout_breadcrumb_label(self):
        if self._site is None:
            return super().get_layout_breadcrumb_label()
        return self._site.code

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault(
            "form",
            SiteForm(
                initial={
                    "code": self._site.code,
                    "name": self._site.name,
                    "investigator": self._site.investigator,
                    "study_id": self._site.study_id,
                    "is_active": self._site.is_active,
                },
                study_choices=self.get_study_choices(self.request.user),
            ),
        )
        context["form_title"] = self._site.code
        context["back_url"] = reverse("study:site_detail", kwargs={"site_id": self._site.pk})
        return context

    def post(self, request, *args, **kwargs):
        form = SiteForm(request.POST, study_choices=self.get_study_choices(request.user))
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        if not _user_has_study_access(request.user, form.cleaned_data["study_id"]):
            raise PermissionDenied

        command = UpdateSiteCommand(
            site_id=self._site.pk,
            code=form.cleaned_data["code"],
            name=form.cleaned_data["name"],
            investigator=form.cleaned_data["investigator"],
            study_id=form.cleaned_data["study_id"],
            is_active=form.cleaned_data.get("is_active", self._site.is_active),
            actor_user_id=request.user.pk,
        )

        try:
            self.get_update_site_service().execute(command)
        except SiteCodeAlreadyExistsError:
            form.add_error("code", _("This site code already exists in the selected study."))
            return self.render_to_response(self.get_context_data(form=form))

        return redirect(reverse("study:site_detail", kwargs={"site_id": self._site.pk}))


class SiteDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "site.delete_site"
    raise_exception = True
    delete_site_service_class = DeleteSiteService

    def get_delete_site_service(self):
        return self.delete_site_service_class()

    def post(self, request, *_args, **kwargs):
        site = Site.objects.filter(pk=kwargs["site_id"], deleted=False).first()
        if site is None:
            raise Http404

        if not _user_has_study_access(request.user, site.study_id):
            raise PermissionDenied

        self.get_delete_site_service().execute(
            DeleteSiteCommand(
                site_id=site.pk,
                actor_user_id=request.user.pk,
            ),
        )
        return redirect(reverse("study:site_list"))


# ---------------------------------------------------------------------------
# Site Membership views
# ---------------------------------------------------------------------------

class SiteMembershipListView(LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView):
    permission_required = "site.view_site_membership_list"
    raise_exception = True
    template_name = "study/site/site_memberships.html"
    layout_nav_key = "SITES"
    membership_query_service_class = SiteMembershipQueryService
    site_directory_query_service_class = SiteDirectoryQueryService
    _site = None

    def get_membership_query_service(self):
        return self.membership_query_service_class()

    def get_site_directory_query_service(self):
        return self.site_directory_query_service_class()

    def dispatch(self, request, *args, **kwargs):
        try:
            self._site = self.get_site_directory_query_service().get_site_detail(
                site_id=kwargs["site_id"],
                user=request.user,
            )
        except SiteNotFoundError as exc:
            raise Http404 from exc
        return super().dispatch(request, *args, **kwargs)

    def get_layout_breadcrumb_label(self):
        if self._site is None:
            return super().get_layout_breadcrumb_label()
        return self._site.code

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            self.get_membership_query_service().list_memberships(
                request=self.request,
                site_id=self._site.pk,
            ),
        )
        context["site"] = self._site
        context["back_url"] = reverse("study:site_detail", kwargs={"site_id": self._site.pk})
        return context


class SiteMembershipCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView,
):
    permission_required = "site.create_site_membership"
    raise_exception = True
    template_name = "study/site/site_membership_form.html"
    layout_nav_key = "SITES"
    create_membership_service_class = CreateSiteMembershipService
    site_directory_query_service_class = SiteDirectoryQueryService
    _site = None

    def get_create_membership_service(self):
        return self.create_membership_service_class()

    def get_site_directory_query_service(self):
        return self.site_directory_query_service_class()

    def dispatch(self, request, *args, **kwargs):
        try:
            self._site = self.get_site_directory_query_service().get_site_detail(
                site_id=kwargs["site_id"],
                user=request.user,
            )
        except SiteNotFoundError as exc:
            raise Http404 from exc
        return super().dispatch(request, *args, **kwargs)

    def get_layout_breadcrumb_label(self):
        if self._site is None:
            return super().get_layout_breadcrumb_label()
        return self._site.code

    def _get_user_choices(self):
        return [
            (u.pk, f"{u.get_full_name() or u.username} ({u.username})")
            for u in User.objects.filter(is_active=True).order_by("username")
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("form", SiteMembershipForm(user_choices=self._get_user_choices()))
        context["site"] = self._site
        context["form_title"] = _("Add Member")
        context["back_url"] = reverse("study:membership_list", kwargs={"site_id": self._site.pk})
        return context

    def post(self, request, *args, **kwargs):
        form = SiteMembershipForm(request.POST, user_choices=self._get_user_choices())
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        command = CreateSiteMembershipCommand(
            site_id=self._site.pk,
            study_id=self._site.study_id,
            user_id=form.cleaned_data["user_id"],
            actor_user_id=request.user.pk,
        )

        try:
            self.get_create_membership_service().execute(command)
        except SiteMembershipAlreadyExistsError:
            form.add_error("user_id", _("This user is already a member of this site."))
            return self.render_to_response(self.get_context_data(form=form))
        except SiteNotFoundError as exc:
            raise Http404 from exc

        return redirect(reverse("study:membership_list", kwargs={"site_id": self._site.pk}))


class SiteMembershipDetailView(
    LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView,
):
    permission_required = "site.view_site_membership_detail"
    raise_exception = True
    template_name = "study/site/site_membership_detail.html"
    layout_nav_key = "SITES"
    membership_query_service_class = SiteMembershipQueryService
    site_directory_query_service_class = SiteDirectoryQueryService
    _site = None
    _membership = None

    def get_membership_query_service(self):
        return self.membership_query_service_class()

    def get_site_directory_query_service(self):
        return self.site_directory_query_service_class()

    def dispatch(self, request, *args, **kwargs):
        try:
            self._site = self.get_site_directory_query_service().get_site_detail(
                site_id=kwargs["site_id"],
                user=request.user,
            )
        except SiteNotFoundError as exc:
            raise Http404 from exc

        try:
            self._membership = self.get_membership_query_service().get_membership_detail(
                membership_id=kwargs["membership_id"],
                site_id=self._site.pk,
            )
        except SiteMembershipNotFoundError as exc:
            raise Http404 from exc

        return super().dispatch(request, *args, **kwargs)

    def get_layout_breadcrumb_label(self):
        if self._membership is None:
            return super().get_layout_breadcrumb_label()
        return getattr(self._membership.user, "username", "")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["membership"] = self._membership
        context["site"] = self._site
        context["back_url"] = reverse("study:membership_list", kwargs={"site_id": self._site.pk})
        context["delete_url"] = reverse(
            "study:membership_delete",
            kwargs={"site_id": self._site.pk, "membership_id": self._membership.pk},
        )
        return context


class SiteMembershipDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "site.delete_site_membership"
    raise_exception = True
    delete_membership_service_class = DeleteSiteMembershipService

    def get_delete_membership_service(self):
        return self.delete_membership_service_class()

    def post(self, request, *_args, **kwargs):
        site = Site.objects.filter(pk=kwargs["site_id"], deleted=False).first()
        if site is None:
            raise Http404

        if not _user_has_study_access(request.user, site.study_id):
            raise PermissionDenied

        try:
            self.get_delete_membership_service().execute(
                DeleteSiteMembershipCommand(
                    membership_id=kwargs["membership_id"],
                    actor_user_id=request.user.pk,
                ),
            )
        except SiteMembershipNotFoundError as exc:
            raise Http404 from exc

        return redirect(reverse("study:membership_list", kwargs={"site_id": kwargs["site_id"]}))
