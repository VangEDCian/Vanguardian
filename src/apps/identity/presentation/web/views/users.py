import json

from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View

from apps.audit.public import build_audit_request_context
from apps.identity.application import (
    CreateIdentityUserService,
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
    RestoreIdentityUserService,
    UpdateIdentityUserDetailService,
    serialize_identity_user_snapshot,
)
from apps.identity.models import User
from apps.identity.presentation.web.forms import (
    IdentityUserCreateForm,
    IdentityUserDetailForm,
)
from apps.identity.presentation.web.mappers.user_commands import (
    to_create_identity_user_command,
    to_delete_identity_user_command,
    to_restore_identity_user_command,
    to_update_identity_user_detail_command,
)
from apps.identity.public import ResourceContext
from apps.shared.navigation import get_default_study_id, user_can_access_permission
from apps.shared.views.generic import AuthenticateTemplateContextMixin, AuthenticateTemplateView


class IdentityUsersView(AuthenticateTemplateView):
    permission_required = "identity.view_user_list"
    require_study_context = False
    raise_exception = True
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

    def get_permission_resource_context(self):
        study_id = get_default_study_id(self.request)
        if study_id is None:
            return None

        from apps.identity.public import ResourceContext

        return ResourceContext(study_id=study_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            self.get_user_directory_query_service().list_users(
                actor_user=self.request.user,
                search_query=self.request.GET.get("q", ""),
                filter_key=self.request.GET.get("filter", ""),
                sort_key=self.request.GET.get("sort", "username"),
                sort_direction=self.request.GET.get("direction", "asc"),
            )
        )
        context["can_create_user"] = user_can_access_permission(
            self.request.user,
            "identity.create_user",
            study_id=get_default_study_id(self.request),
        )
        return context


class IdentityUserCreateView(AuthenticateTemplateView):
    permission_required = "identity.create_user"
    require_study_context = False
    raise_exception = True
    template_name = "identity/user_create.html"
    layout_nav_key = "USERS"
    layout_breadcrumb_label = _("NEW USER")
    user_create_form_class = IdentityUserCreateForm
    create_identity_user_service_class = CreateIdentityUserService
    user_directory_query_service_class = IdentityUserDirectoryQueryService
    identity_user_audit_service_class = IdentityUserAuditService

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_user_create_form(self, *args, **kwargs):
        selected_study_ids = kwargs.pop("selected_study_ids", None)
        if selected_study_ids is None and args:
            selected_study_ids = args[0].getlist("studies")
        return self.user_create_form_class(
            *args,
            study_choices=self._build_study_choices(),
            site_choices=self._build_site_choices(selected_study_ids=selected_study_ids or ()),
            **kwargs,
        )

    def get_create_identity_user_service(self):
        return self.create_identity_user_service_class()

    def get_user_directory_query_service(self):
        return self.user_directory_query_service_class()

    def get_identity_user_audit_service(self):
        return self.identity_user_audit_service_class()

    def get_permission_resource_context(self):
        study_id = get_default_study_id(self.request)
        if study_id is None:
            return None

        from apps.identity.public import ResourceContext

        return ResourceContext(study_id=study_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("form", self.get_user_create_form())
        form = context["form"]
        context["back_url"] = reverse("identity:users")
        context["create_url"] = reverse("identity:user_create")
        context["can_manage_permissions"] = self._can_manage_permissions(self.request.user)
        context["can_manage_permission_groups"] = self._can_manage_permission_groups(
            self.request.user,
            study_id=get_default_study_id(self.request),
        )
        context["permission_group_options"] = self._build_select_options(
            form.fields["permission_groups"].choices,
            form["permission_groups"].value() or [],
        )
        context["study_options"] = self._build_select_options(
            form.fields["studies"].choices,
            form["studies"].value() or [],
        )
        context["site_options"] = self._build_site_option_dicts(
            selected_study_ids=form["studies"].value() or [],
            selected_site_ids=form["sites"].value() or [],
        )
        context["has_selected_studies"] = bool(form["studies"].value())
        context["api_studies_url"] = reverse("identity:api_studies")
        context["api_study_sites_url"] = reverse("identity:api_study_sites")
        context["study_membership_role_options"] = self.get_user_directory_query_service().list_role_option_dicts(
            scope_level="STUDY",
            study_ids=self._accessible_study_ids(),
        )
        context["site_membership_role_options"] = self.get_user_directory_query_service().list_role_option_dicts(
            scope_level="STUDY_SITE",
            study_ids=self._accessible_study_ids(),
        )
        context["selected_study_role_ids"] = self._extract_role_map_from_payload(
            getattr(self.request, "POST", {}),
            "study_roles",
        )
        context["selected_site_role_ids"] = self._extract_role_map_from_payload(
            getattr(self.request, "POST", {}),
            "site_roles",
        )
        return context

    def post(self, request, *args, **kwargs):
        form = self.get_user_create_form(request.POST, selected_study_ids=request.POST.getlist("studies"))
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        try:
            created_user = self.get_create_identity_user_service().execute(
                to_create_identity_user_command(
                    actor_user_id=request.user.pk,
                    username=form.cleaned_data["username"],
                    password=form.cleaned_data["password"],
                    first_name=form.cleaned_data["first_name"],
                    last_name=form.cleaned_data["last_name"],
                    email=form.cleaned_data["email"],
                    phone_number=form.cleaned_data["phone_number"],
                    study_ids=tuple(form.cleaned_data.get("studies", ())),
                    site_ids=tuple(form.cleaned_data.get("sites", ())),
                    study_role_ids_by_study_id=self._extract_role_map_from_payload(request.POST, "study_roles"),
                    site_role_ids_by_site_id=self._extract_role_map_from_payload(request.POST, "site_roles"),
                    can_manage_permissions=self._can_manage_permissions(request.user),
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

    def _build_study_choices(self):
        return self.get_user_directory_query_service().list_study_choices(user=self.request.user)

    def _build_site_choices(self, *, selected_study_ids):
        selected_study_ids_set = {str(study_id) for study_id in (selected_study_ids or ()) if str(study_id).strip()}
        if not selected_study_ids_set:
            return ()

        allowed_study_ids = set(self._accessible_study_ids())
        selected_study_ids_int = [
            int(study_id)
            for study_id in selected_study_ids_set
            if study_id.isdigit() and int(study_id) in allowed_study_ids
        ]
        return [
            (str(site.pk), f"{site.code} - {site.name}".strip())
            for site in self.get_user_directory_query_service().repository.list_accessible_sites_for_user(
                self.request.user,
                study_ids=selected_study_ids_int,
            )
        ]

    def _build_site_option_dicts(self, *, selected_study_ids, selected_site_ids):
        selected_study_ids_set = {str(study_id) for study_id in (selected_study_ids or ()) if str(study_id).strip()}
        if not selected_study_ids_set:
            return ()
        allowed_study_ids = set(self._accessible_study_ids())
        selected_study_ids_int = [
            int(study_id)
            for study_id in selected_study_ids_set
            if study_id.isdigit() and int(study_id) in allowed_study_ids
        ]
        selected_site_ids_set = {str(site_id) for site_id in selected_site_ids or ()}
        return [
            {
                "value": str(site.pk),
                "label": f"{site.code} - {site.name}".strip(),
                "study_id": str(site.study_id),
                "selected": str(site.pk) in selected_site_ids_set,
            }
            for site in self.get_user_directory_query_service().repository.list_accessible_sites_for_user(
                self.request.user,
                study_ids=selected_study_ids_int,
            )
        ]

    def _can_manage_permissions(self, request_user):
        study_id = get_default_study_id(self.request)
        return user_can_access_permission(
            request_user,
            "identity.create_user",
            study_id=study_id,
        ) or user_can_access_permission(
            request_user,
            "identity.update_user",
            study_id=study_id,
        )

    @staticmethod
    def _can_manage_permission_groups(request_user, study_id=None):
        return (
            request_user.is_superuser
            or user_can_access_permission(
                request_user,
                "identity.create_user",
                study_id=study_id,
            )
            or user_can_access_permission(
                request_user,
                "identity.update_user",
                study_id=study_id,
            )
        )

    def _accessible_study_ids(self):
        return tuple(
            self.get_user_directory_query_service()
            .repository.list_accessible_studies_for_user(self.request.user)
            .values_list("pk", flat=True)
        )

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

    @staticmethod
    def _extract_role_map_from_payload(payload, field_name):
        if not payload:
            return {}
        if isinstance(payload, dict) and isinstance(payload.get(field_name), dict):
            return {
                str(scope_id): str(role_id)
                for scope_id, role_id in payload[field_name].items()
                if str(scope_id).strip() and str(role_id).strip()
            }
        prefix = f"{field_name}["
        selected = {}
        keys = payload.keys() if hasattr(payload, "keys") else ()
        for key in keys:
            raw_key = str(key)
            if not raw_key.startswith(prefix) or not raw_key.endswith("]"):
                continue
            scope_id = raw_key[len(prefix):-1].strip()
            role_id = payload.get(key)
            if scope_id and str(role_id or "").strip():
                selected[scope_id] = str(role_id).strip()
        return selected


class IdentityUserDetailView(AuthenticateTemplateView):
    permission_required = "identity.view_user_detail"
    require_study_context = False
    raise_exception = True
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
        selected_study_ids = kwargs.pop("selected_study_ids", None)
        if selected_study_ids is None and args:
            selected_study_ids = args[0].get("studies", ())
        return self.user_detail_form_class(
            *args,
            study_choices=[
                (study_option["value"], study_option["label"])
                for study_option in detail_user["study_options"]
            ],
            site_choices=self._build_site_choices_for_detail(
                selected_study_ids=selected_study_ids or detail_user["selected_study_ids"],
                detail_user=detail_user,
            ),
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

    @staticmethod
    def _extract_role_map_from_payload(payload, field_name):
        return IdentityUserCreateView._extract_role_map_from_payload(payload, field_name)

    def dispatch(self, request, *args, **kwargs):
        self.include_deleted = self._include_deleted_users(request)
        if self.include_deleted and not user_can_access_permission(
            request.user,
            "identity.restore_user",
            study_id=get_default_study_id(request),
        ):
            raise PermissionDenied

        try:
            self.detail_view_model = self.get_user_directory_query_service().get_user_detail(
                user_id=kwargs["user_id"],
                include_deleted=self.include_deleted,
                actor_user=request.user,
            )
        except IdentityUserNotFoundError as exc:
            raise Http404 from exc

        target_user = User.objects.filter(pk=kwargs["user_id"]).first()
        if not self.get_user_directory_query_service().repository.user_is_accessible_to_user(
            actor_user=request.user,
            target_user=target_user,
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_permission_resource_context(self):
        study_id = get_default_study_id(self.request)
        if study_id is None:
            return None
        return ResourceContext(study_id=study_id)

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
            context["can_manage_permission_groups"] = self._can_manage_permission_groups(
                self.request.user,
                study_id=get_default_study_id(self.request),
            )
            context["can_delete_user"] = self._can_delete_user(self.request.user)
            context["can_restore_user"] = self._can_restore_user(self.request.user)
            context["delete_url"] = reverse("identity:user_delete", kwargs={"user_id": self.detail_view_model["detail_user"]["id"]})
            context["restore_url"] = reverse("identity:user_restore", kwargs={"user_id": self.detail_view_model["detail_user"]["id"]})
            context["has_selected_studies"] = bool(self.detail_view_model["detail_user"]["selected_study_ids"])
            context["api_studies_url"] = reverse("identity:api_studies")
            context["api_study_sites_url"] = reverse("identity:api_study_sites")
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

        form = self.get_user_detail_form(payload, selected_study_ids=payload.get("studies", ()))
        if not form.is_valid():
            return JsonResponse(
                {"errors": form.errors.get_json_data()},
                status=400,
            )

        target_user = User.objects.filter(pk=self.kwargs["user_id"]).first()
        if target_user is None:
            raise Http404

        before_data = serialize_identity_user_snapshot(target_user)

        new_password = form.cleaned_data.get("new_password") or None

        try:
            updated_user = self.get_update_user_detail_service().execute(
                to_update_identity_user_detail_command(
                    user_id=target_user.pk,
                    actor_user_id=request.user.pk,
                    first_name=form.cleaned_data["first_name"],
                    last_name=form.cleaned_data["last_name"],
                    email=form.cleaned_data["email"],
                    phone_number=form.cleaned_data["phone_number"],
                    is_active=form.cleaned_data["is_active"],
                    study_ids=tuple(form.cleaned_data.get("studies", ())),
                    site_ids=tuple(form.cleaned_data.get("sites", ())),
                    study_role_ids_by_study_id=self._extract_role_map_from_payload(payload, "study_roles"),
                    site_role_ids_by_site_id=self._extract_role_map_from_payload(payload, "site_roles"),
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
            user_can_access_permission(
                request_user,
                "identity.update_user",
                study_id=get_default_study_id(self.request),
            )
            and request_user.pk != detail_user_id
            and not self.detail_view_model["detail_user"]["is_deleted"]
        )

    def _can_delete_user(self, request_user):
        detail_user_id = self.detail_view_model["detail_user"]["id"]
        return (
            user_can_access_permission(
                request_user,
                "identity.delete_user",
                study_id=get_default_study_id(self.request),
            )
            and request_user.pk != detail_user_id
            and not self.detail_view_model["detail_user"]["is_deleted"]
        )

    def _can_restore_user(self, request_user):
        detail_user_id = self.detail_view_model["detail_user"]["id"]
        return (
            user_can_access_permission(
                request_user,
                "identity.restore_user",
                study_id=get_default_study_id(self.request),
            )
            and request_user.pk != detail_user_id
            and self.detail_view_model["detail_user"]["is_deleted"]
        )

    def _can_manage_permissions(self, request_user):
        detail_user_id = self.detail_view_model["detail_user"]["id"]
        return (
            user_can_access_permission(
                request_user,
                "identity.update_user",
                study_id=get_default_study_id(self.request),
            )
            and request_user.pk != detail_user_id
            and not self.detail_view_model["detail_user"]["is_deleted"]
        )

    @staticmethod
    def _can_manage_permission_groups(request_user, study_id=None):
        return (
            request_user.is_superuser
            or user_can_access_permission(
                request_user,
                "identity.create_user",
                study_id=study_id,
            )
            or user_can_access_permission(
                request_user,
                "identity.update_user",
                study_id=study_id,
            )
        )

    def _permission_group_ids_for_update(self, form):
        if self._can_manage_permission_groups(
            self.request.user,
            study_id=get_default_study_id(self.request),
        ):
            return tuple(form.cleaned_data.get("permission_groups", ()))
        return tuple(self.detail_view_model["detail_user"].get("selected_permission_group_ids", ()))

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

    def _build_site_choices_for_detail(self, *, selected_study_ids, detail_user):
        selected_study_ids_set = {str(study_id) for study_id in (selected_study_ids or ()) if str(study_id).strip()}
        if not selected_study_ids_set:
            return [
                (site_option["value"], site_option["label"])
                for site_option in detail_user["site_options"]
            ]

        selected_study_ids_int = [int(study_id) for study_id in selected_study_ids_set if study_id.isdigit()]
        return [
            (str(site.pk), f"{site.code} - {site.name}".strip())
            for site in self.get_user_directory_query_service().repository.list_accessible_sites_for_user(
                self.request.user,
                study_ids=selected_study_ids_int,
            )
        ]


class IdentityStudyOptionsApiView(AuthenticateTemplateContextMixin, View):
    permission_required = "study.view_study_list"
    require_study_context = False
    raise_exception = True
    user_directory_query_service_class = IdentityUserDirectoryQueryService

    def get_user_directory_query_service(self):
        return self.user_directory_query_service_class()

    def get_permission_resource_context(self):
        study_id = get_default_study_id(self.request)
        if study_id is None:
            return None
        return ResourceContext(study_id=study_id)

    def get(self, request, *args, **kwargs):
        search_query = (request.GET.get("q") or "").strip()
        studies = self.get_user_directory_query_service().repository.list_accessible_studies_for_user(
            request.user,
            search_query=search_query,
        )[:50]

        return JsonResponse(
            {
                "results": [
                    {
                        "id": str(study.pk),
                        "text": f"{study.code} - {study.name}".strip(),
                    }
                    for study in studies
                ],
            }
        )


class IdentityStudySiteOptionsApiView(AuthenticateTemplateContextMixin, View):
    permission_required = ("study.view_study_list", "site.view_site_list")
    require_study_context = False
    raise_exception = True
    user_directory_query_service_class = IdentityUserDirectoryQueryService

    def get_user_directory_query_service(self):
        return self.user_directory_query_service_class()

    def get_permission_resource_context(self):
        study_ids = _normalize_study_ids_param(self.request.GET.get("study_ids"))
        study_id = study_ids[0] if study_ids else get_default_study_id(self.request)
        if study_id is None:
            return None
        return ResourceContext(study_id=study_id)

    def get(self, request, *args, **kwargs):
        study_ids = _normalize_study_ids_param(request.GET.get("study_ids"))
        if not study_ids:
            return JsonResponse({"results": []})

        search_query = (request.GET.get("q") or "").strip()
        sites = self.get_user_directory_query_service().repository.list_accessible_sites_for_user(
            request.user,
            study_ids=study_ids,
            search_query=search_query,
        )[:100]

        return JsonResponse(
            {
                "results": [
                    {
                        "id": str(site.pk),
                        "text": f"{site.code} - {site.name}".strip(),
                        "study_id": str(site.study_id),
                    }
                    for site in sites
                ],
            }
        )


def _normalize_study_ids_param(raw_value):
    if raw_value is None:
        return []
    normalized_values = []
    for value in str(raw_value).split(","):
        normalized_value = value.strip()
        if normalized_value.isdigit():
            normalized_values.append(int(normalized_value))
    return normalized_values


class IdentityUserDeleteView(AuthenticateTemplateContextMixin, View):
    permission_required = "identity.delete_user"
    require_study_context = False
    raise_exception = True
    delete_user_service_class = DeleteIdentityUserService
    identity_user_audit_service_class = IdentityUserAuditService

    def get_delete_user_service(self):
        return self.delete_user_service_class()

    def get_identity_user_audit_service(self):
        return self.identity_user_audit_service_class()

    def get_permission_resource_context(self):
        study_id = get_default_study_id(self.request)
        if study_id is None:
            return None
        return ResourceContext(study_id=study_id)

    def post(self, request, *args, **kwargs):
        if request.user.pk == kwargs["user_id"]:
            raise PermissionDenied

        target_user = User.objects.filter(pk=kwargs["user_id"]).first()
        if target_user is None:
            raise Http404

        before_data = serialize_identity_user_snapshot(target_user)
        self.get_delete_user_service().execute(
            to_delete_identity_user_command(
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
    permission_required = "identity.restore_user"
    require_study_context = False
    raise_exception = True
    restore_user_service_class = RestoreIdentityUserService
    identity_user_audit_service_class = IdentityUserAuditService

    def get_restore_user_service(self):
        return self.restore_user_service_class()

    def get_identity_user_audit_service(self):
        return self.identity_user_audit_service_class()

    def get_permission_resource_context(self):
        study_id = get_default_study_id(self.request)
        if study_id is None:
            return None
        return ResourceContext(study_id=study_id)

    def post(self, request, *args, **kwargs):
        if request.user.pk == kwargs["user_id"]:
            raise PermissionDenied

        target_user = User.objects.filter(pk=kwargs["user_id"]).first()
        if target_user is None:
            raise Http404

        before_data = serialize_identity_user_snapshot(target_user)

        try:
            restored_user = self.get_restore_user_service().execute(
                to_restore_identity_user_command(
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
