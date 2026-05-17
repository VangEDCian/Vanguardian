from django.utils.translation import gettext_lazy as _

from apps.identity.infrastructure.repositories import DjangoIdentityUserRepository


class CurrentUserProfileSummaryService:
    repository_class = DjangoIdentityUserRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def build(self, user):
        full_name = user.get_full_name() or getattr(user, "display_name", "") or user.get_username()
        return {
            "display_name": getattr(user, "display_name", "") or full_name,
            "full_name": full_name,
            "username": user.get_username(),
            "email": user.email or _("No email configured"),
            "role_label": self._build_role_label(user),
            "is_superuser": bool(user.is_superuser),
            "is_staff": bool(user.is_staff),
            "is_active": bool(user.is_active),
            "status_label": _("Active") if user.is_active else _("Inactive"),
            "administrator_label": _("Administrator"),
            "staff_label": _("Staff"),
            "initials": _build_initials(full_name),
            "date_joined": user.date_joined,
            "last_login": user.last_login,
        }

    def _build_role_label(self, user):
        role_names = [user_role.role.name for user_role in self.repository.list_user_roles(user)]
        if role_names:
            return ", ".join(role_names)
        return "—"


def _build_initials(value):
    words = [word for word in (value or "").replace("@", " ").split() if word]
    if not words:
        return "U"
    if len(words) == 1:
        return words[0][:2].upper()
    return f"{words[0][0]}{words[-1][0]}".upper()
