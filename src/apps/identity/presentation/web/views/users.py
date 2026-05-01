import json

from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View

from apps.audit.public import build_audit_request_context
from apps.identity.application import (
    CreateIdentityUserCommand,
    CreateIdentityUserService,
    DeleteIdentityUserCommand,
    DeleteIdentityUserService,
    IdentityUserAuditService,
    IdentityUserDirectoryQueryService,
    IdentityUserEmailAlreadyExistsError,
    IdentityUserFilterActiveQueryService,
    IdentityUserFilterInactiveQueryService,
    IdentityUsernameAlreadyExistsError,
    IdentityUserNotFoundError,
    IdentityUserPhoneNumberAlreadyExistsError,
    IdentityUserRestoreDataNotFoundError,
    RestoreIdentityUserCommand,
    RestoreIdentityUserService,
    UpdateIdentityUserDetailCommand,
    UpdateIdentityUserDetailService,
    serialize_identity_user_snapshot,
)
from apps.identity.models import User
from apps.identity.presentation.web.forms import (
    IdentityUserCreateForm,
    IdentityUserDetailForm,
)
from apps.shared.views.generic import AuthenticateTemplateContextMixin, AuthenticateTemplateView


class IdentityUsersView(AuthenticateTemplateView):
    template_name = "identity/users.html"
    layout_nav_key = "USERS"
    layout_breadcrumb_label = _("USERS")
    user_directory_query_service_class = IdentityUserDirectoryQueryService
    registered_filter_query_service_classes = (
        IdentityUserFilterActiveQueryService,
        IdentityUserFilterInactiveQueryService,
    )

    def get_user_directory_query_service(self):
        return self.user_directory_query_service_class(
            registered_filter_query_service_classes=self.registered_filter_query_service_classes
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            self.get_user_directory_query_service().list_users(
                search_query=self.request.GET.get("q", ""),
                filter_key=self.request.GET.get("filter", ""),
                sort_key=self.request.GET.get("sort", "username"),
                sort_direction=self.request.GET.get("direction", "asc"),
            )
        )
        return context


class IdentityUserCreateView(AuthenticateTemplateView):
    template_name = "identity/user_create.html"
    layout_nav_key = "USERS"
    layout_breadcrumb_label = _("NEW USER")
    user_create_form_class = IdentityUserCreateForm
    create_identity_user_service_class = CreateIdentityUserService
    identity_user_audit_service_class = IdentityUserAuditService

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_user_create_form(self, *args, **kwargs):
        return self.user_create_form_class(
            *args,
            role_choices=self._build_role_choices(),
            permission_group_choices=self._build_permission_group_choices(),
            **kwargs,
        )

    def get_create_identity_user_service(self):
        return self.create_identity_user_service_class()

    def get_identity_user_audit_service(self):
        return self.identity_user_audit_service_class()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("form", self.get_user_create_form())
        form = context["form"]
        context["back_url"] = reverse("identity:users")
        context["create_url"] = reverse("identity:user_create")
        context["can_manage_permissions"] = self.request.user.is_superuser
        context["role_options"] = self._build_select_options(
            form.fields["role"].choices,
            [form["role"].value()],
        )
        context["permission_group_options"] = self._build_select_options(
            form.fields["permission_groups"].choices,
            form["permission_groups"].value() or [],
        )
        return context

    def post(self, request, *args, **kwargs):
        form = self.get_user_create_form(request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        try:
            created_user = self.get_create_identity_user_service().execute(
                CreateIdentityUserCommand(
                    actor_user_id=request.user.pk,
                    username=form.cleaned_data["username"],
                    password=form.cleaned_data["password"],
                    first_name=form.cleaned_data["first_name"],
                    last_name=form.cleaned_data["last_name"],
                    email=form.cleaned_data["email"],
                    phone_number=form.cleaned_data["phone_number"],
                    role_key=form.cleaned_data.get("role") or "user",
                    permission_group_ids=tuple(form.cleaned_data.get("permission_groups", ())),
                    can_manage_permissions=request.user.is_superuser,
                )
            )
        except IdentityUsernameAlreadyExistsError:
            form.add_error("username", _("This username is already in use."))
            return self.render_to_response(self.get_context_data(form=form))
        except IdentityUserEmailAlreadyExistsError:
            form.add_error("email", _("This email address is already in use."))
            return self.render_to_response(self.get_context_data(form=form))
        except IdentityUserPhoneNumberAlreadyExistsError:
            form.add_error("phone_number", _("This phone number is already in use."))
            return self.render_to_response(self.get_context_data(form=form))

        self.get_identity_user_audit_service().record_created(
            user=created_user,
            **build_audit_request_context(request),
        )
        return redirect(reverse("identity:user_detail", kwargs={"user_id": created_user.pk}))

    @staticmethod
    def _build_role_choices():
        return [
            ("administrator", _("Administrator")),
            ("staff", _("Staff")),
            ("user", _("User")),
        ]

    @staticmethod
    def _build_permission_group_choices():
        return [(str(group.pk), group.name) for group in Group.objects.order_by("name")]

    @staticmethod
    def _build_select_options(choices, selected_values):
        normalized_selected_values = {str(value) for value in selected_values if value not in (None, "")}
        return [
            {
                "value": str(value),
                "label": label,
                "selected": str(value) in normalized_selected_values,
            }
            for value, label in choices
        ]


class IdentityUserDetailView(AuthenticateTemplateView):
    template_name = "identity/user_detail.html"
    layout_nav_key = "USERS"
    user_directory_query_service_class = IdentityUserDirectoryQueryService
    user_detail_form_class = IdentityUserDetailForm
    update_user_detail_service_class = UpdateIdentityUserDetailService
    delete_user_service_class = DeleteIdentityUserService
    restore_user_service_class = RestoreIdentityUserService
    identity_user_audit_service_class = IdentityUserAuditService
    detail_view_model = None
    include_deleted = False

    def get_user_directory_query_service(self):
        return self.user_directory_query_service_class()

    def get_user_detail_form(self, *args, **kwargs):
        detail_user = self.detail_view_model["detail_user"]
        return self.user_detail_form_class(
            *args,
            role_choices=[
                (role_option["value"], role_option["label"])
                for role_option in detail_user["role_options"]
            ],
            permission_group_choices=[
                (permission_group_option["value"], permission_group_option["label"])
                for permission_group_option in detail_user["permission_group_options"]
            ],
            **kwargs,
        )

    def get_update_user_detail_service(self):
        return self.update_user_detail_service_class()

    def get_delete_user_service(self):
        return self.delete_user_service_class()

    def get_restore_user_service(self):
        return self.restore_user_service_class()

    def get_identity_user_audit_service(self):
        return self.identity_user_audit_service_class()

    def dispatch(self, request, *args, **kwargs):
        self.include_deleted = self._include_deleted_users(request)
        if self.include_deleted and not request.user.is_superuser:
            raise PermissionDenied

        try:
            self.detail_view_model = self.get_user_directory_query_service().get_user_detail(
                user_id=kwargs["user_id"],
                include_deleted=self.include_deleted,
            )
        except IdentityUserNotFoundError as exc:
            raise Http404 from exc
        return super().dispatch(request, *args, **kwargs)

    def get_layout_breadcrumb_label(self):
        if self.detail_view_model is None:
            return super().get_layout_breadcrumb_label()
        return self.detail_view_model["layout_breadcrumb_label"]

    def get_layout_show_breadcrumb_trail(self):
        return False

    def get_layout_detail_meta_items(self):
        if self.detail_view_model is None:
            return super().get_layout_detail_meta_items()
        return self.detail_view_model.get("layout_detail_meta_items", ())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.detail_view_model is not None:
            context["detail_user"] = self.detail_view_model["detail_user"]
            context["can_update_detail"] = self._can_update_detail(self.request.user)
            context["can_manage_permissions"] = self._can_manage_permissions(self.request.user)
            context["can_delete_user"] = self._can_delete_user(self.request.user)
            context["can_restore_user"] = self._can_restore_user(self.request.user)
            context["delete_url"] = reverse("identity:user_delete", kwargs={"user_id": self.detail_view_model["detail_user"]["id"]})
            context["restore_url"] = reverse("identity:user_restore", kwargs={"user_id": self.detail_view_model["detail_user"]["id"]})
        return context

    def put(self, request, *args, **kwargs):
        if not self._can_update_detail(request.user):
            return JsonResponse(
                {"detail": str(_("You do not have permission to update this user."))},
                status=403,
            )

        payload = self._parse_request_payload(request)
        if payload is None:
            return JsonResponse(
                {"detail": str(_("Invalid request payload."))},
                status=400,
            )

        form = self.get_user_detail_form(payload)
        if not form.is_valid():
            return JsonResponse(
                {"errors": form.errors.get_json_data()},
                status=400,
            )

        target_user = User.objects.prefetch_related("groups").filter(pk=self.kwargs["user_id"]).first()
        if target_user is None:
            raise Http404

        before_data = serialize_identity_user_snapshot(target_user)

        new_password = form.cleaned_data.get("new_password") or None

        try:
            updated_user = self.get_update_user_detail_service().execute(
                UpdateIdentityUserDetailCommand(
                    user_id=target_user.pk,
                    actor_user_id=request.user.pk,
                    first_name=form.cleaned_data["first_name"],
                    last_name=form.cleaned_data["last_name"],
                    email=form.cleaned_data["email"],
                    phone_number=form.cleaned_data["phone_number"],
                    is_active=form.cleaned_data["is_active"],
                    role_key=form.cleaned_data.get("role") or target_user_role_key(target_user),
                    permission_group_ids=tuple(form.cleaned_data.get("permission_groups", ())),
                    can_manage_permissions=self._can_manage_permissions(request.user),
                    new_password=new_password,
                )
            )
        except IdentityUserEmailAlreadyExistsError:
            form.add_error("email", _("This email address is already in use."))
            return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
        except IdentityUserPhoneNumberAlreadyExistsError:
            form.add_error("phone_number", _("This phone number is already in use."))
            return JsonResponse({"errors": form.errors.get_json_data()}, status=400)

        self.get_identity_user_audit_service().record_updated(
            user=updated_user,
            before_data=before_data,
            **build_audit_request_context(request),
        )

        if new_password:
            self.get_identity_user_audit_service().record_admin_set_password(
                user=updated_user,
                **build_audit_request_context(request),
            )

        return JsonResponse(
            {
                "detail": str(_("User details saved successfully.")),
                "redirect_url": self.detail_view_model["detail_user"]["update_url"],
            }
        )

    def _can_update_detail(self, request_user):
        detail_user_id = self.detail_view_model["detail_user"]["id"]
        return (
            request_user.is_superuser
            and request_user.pk != detail_user_id
            and not self.detail_view_model["detail_user"]["is_deleted"]
        )

    def _can_delete_user(self, request_user):
        detail_user_id = self.detail_view_model["detail_user"]["id"]
        return (
            request_user.is_superuser
            and request_user.pk != detail_user_id
            and not self.detail_view_model["detail_user"]["is_deleted"]
        )

    def _can_restore_user(self, request_user):
        detail_user_id = self.detail_view_model["detail_user"]["id"]
        return (
            request_user.is_superuser
            and request_user.pk != detail_user_id
            and self.detail_view_model["detail_user"]["is_deleted"]
        )

    def _can_manage_permissions(self, request_user):
        detail_user_id = self.detail_view_model["detail_user"]["id"]
        return (
            request_user.is_superuser
            and request_user.pk != detail_user_id
            and not self.detail_view_model["detail_user"]["is_deleted"]
        )

    @staticmethod
    def _parse_request_payload(request):
        if not request.body:
            return {}

        try:
            return json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    @staticmethod
    def _include_deleted_users(request):
        return (request.GET.get("include_deleted") or "").strip().lower() in {"1", "true", "yes"}


def target_user_role_key(user):
    if user.is_superuser:
        return "administrator"
    if user.is_staff:
        return "staff"
    return "user"


class IdentityUserDeleteView(AuthenticateTemplateContextMixin, View):
    delete_user_service_class = DeleteIdentityUserService
    identity_user_audit_service_class = IdentityUserAuditService

    def get_delete_user_service(self):
        return self.delete_user_service_class()

    def get_identity_user_audit_service(self):
        return self.identity_user_audit_service_class()

    def post(self, request, *args, **kwargs):
        if not request.user.is_superuser or request.user.pk == kwargs["user_id"]:
            raise PermissionDenied

        target_user = User.objects.prefetch_related("groups").filter(pk=kwargs["user_id"]).first()
        if target_user is None:
            raise Http404

        before_data = serialize_identity_user_snapshot(target_user)
        self.get_delete_user_service().execute(
            DeleteIdentityUserCommand(
                user_id=target_user.pk,
                actor_user_id=request.user.pk,
            )
        )
        self.get_identity_user_audit_service().record_deleted(
            user_id=target_user.pk,
            before_data=before_data,
            **build_audit_request_context(request),
        )
        return redirect(f"{reverse('identity:user_detail', kwargs={'user_id': target_user.pk})}?include_deleted=1")


class IdentityUserRestoreView(AuthenticateTemplateContextMixin, View):
    restore_user_service_class = RestoreIdentityUserService
    identity_user_audit_service_class = IdentityUserAuditService

    def get_restore_user_service(self):
        return self.restore_user_service_class()

    def get_identity_user_audit_service(self):
        return self.identity_user_audit_service_class()

    def post(self, request, *args, **kwargs):
        if not request.user.is_superuser or request.user.pk == kwargs["user_id"]:
            raise PermissionDenied

        target_user = User.objects.prefetch_related("groups").filter(pk=kwargs["user_id"]).first()
        if target_user is None:
            raise Http404

        before_data = serialize_identity_user_snapshot(target_user)

        try:
            restored_user = self.get_restore_user_service().execute(
                RestoreIdentityUserCommand(
                    user_id=target_user.pk,
                    actor_user_id=request.user.pk,
                )
            )
        except (IdentityUserNotFoundError, IdentityUserRestoreDataNotFoundError) as exc:
            raise Http404 from exc

        self.get_identity_user_audit_service().record_restored(
            user=restored_user,
            before_data=before_data,
            **build_audit_request_context(request),
        )
        return redirect(reverse("identity:user_detail", kwargs={"user_id": restored_user.pk}))
