from django.utils.translation import gettext_lazy as _


class IdentityUserFilterQueryService:
    key = ""
    label = _("All")

    def apply(self, queryset):
        return queryset

    def build_option(self):
        return {
            "value": self.key,
            "label": self.label,
        }


class IdentityUserFilterActiveQueryService(IdentityUserFilterQueryService):
    key = "active"
    label = _("Active")

    def apply(self, queryset):
        return queryset.filter(is_active=True)


class IdentityUserFilterInactiveQueryService(IdentityUserFilterQueryService):
    key = "inactive"
    label = _("Inactive")

    def apply(self, queryset):
        return queryset.filter(is_active=False)
