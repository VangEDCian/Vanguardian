from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest
from django.views.generic import TemplateView
from django.views.generic.base import ContextMixin


class AuthenticateTemplateContextMixin(LoginRequiredMixin, ContextMixin):
    login_url = "/login/"
    redirect_field_name = "next"

    layout_nav_key = ""
    layout_breadcrumb_label = ""
    request: HttpRequest

    def get_permission_required(self):
        permission_required = getattr(self, "permission_required", None)
        if permission_required is None:
            return ()
        if isinstance(permission_required, str):
            return (permission_required,)
        return tuple(permission_required)

    def has_permission(self):
        required_permissions = self.get_permission_required()
        if not required_permissions:
            return True
        if self.request.user.has_perms(required_permissions):
            return True

        resource_context = self.get_permission_resource_context()
        user_id = getattr(self.request.user, "pk", None)
        if resource_context is None or user_id is None:
            return False

        from apps.identity.public import can_perform

        return all(
            can_perform(
                user_id=user_id,
                permission_code=permission_code,
                resource_context=resource_context,
            ).is_allowed
            for permission_code in required_permissions
        )

    def get_permission_resource_context(self):
        study_id = self.get_permission_context_int("study_id")
        if study_id is None:
            return None

        from apps.identity.public import ResourceContext

        return ResourceContext(
            study_id=study_id,
            study_site_id=self.get_permission_context_site_id(study_id),
        )

    def get_permission_context_site_id(self, study_id):
        site_id = self.get_permission_context_int("study_site_id") or self.get_permission_context_int("site_id")
        if site_id is not None:
            return site_id

        from apps.shared.context_processors import SiteDropdownHandler

        return SiteDropdownHandler(request=self.request, study_id=study_id).build().selected_id

    def get_permission_context_int(self, key):
        value = (getattr(self, "kwargs", None) or {}).get(key)
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(),
                self.get_login_url(),
                self.get_redirect_field_name(),
            )
        if not self.has_permission():
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["auth_user"] = self.get_auth_user_context()
        context["layout_nav_key"] = self.get_layout_nav_key()
        context["layout_breadcrumb_label"] = self.get_layout_breadcrumb_label()
        context["layout_show_breadcrumb_trail"] = self.get_layout_show_breadcrumb_trail()
        context["layout_detail_meta_items"] = self.get_layout_detail_meta_items()
        return context

    def get_auth_user(self):
        user = getattr(self.request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            return None
        return user

    def get_auth_user_context(self):
        user = self.get_auth_user()
        if user is None:
            return {
                "id": None,
                "username": "",
                "display_name": "",
                "full_name": "",
                "email": "",
                "phone_number": "",
                "is_authenticated": False,
                "is_staff": False,
                "is_superuser": False,
            }

        full_name = user.get_full_name().strip()
        explicit_display_name = getattr(user, "display_name", "").strip()
        display_name = explicit_display_name or full_name or user.get_username()

        return {
            "id": user.pk,
            "username": user.get_username(),
            "display_name": display_name,
            "full_name": full_name,
            "email": getattr(user, "email", "") or "",
            "phone_number": getattr(user, "phone_number", "") or "",
            "is_authenticated": True,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
        }

    def get_layout_nav_key(self):
        return self.layout_nav_key

    def get_layout_breadcrumb_label(self):
        return self.layout_breadcrumb_label

    def get_layout_show_breadcrumb_trail(self):
        return True

    def get_layout_detail_meta_items(self):
        return ()


class AuthenticateTemplateView(AuthenticateTemplateContextMixin, TemplateView):
    """Concrete template view that includes the shared authenticated layout context."""
