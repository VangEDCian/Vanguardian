from django.views.generic import TemplateView


class AuthenticateTemplateView(TemplateView):
    """
    Shared template base that always exposes a stable user payload for layout
    rendering and future template helpers.
    """

    layout_nav_key = ""
    layout_breadcrumb_label = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["auth_user"] = self.get_auth_user_context()
        context["layout_nav_key"] = self.get_layout_nav_key()
        context["layout_breadcrumb_label"] = self.get_layout_breadcrumb_label()
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
