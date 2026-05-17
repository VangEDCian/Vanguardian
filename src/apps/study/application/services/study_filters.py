from django.utils.translation import gettext_lazy as _


class StudyFilterQueryService:
    key = ""
    label = _("All")

    def apply(self, queryset):
        return queryset

    def build_option(self):
        return {
            "value": self.key,
            "label": self.label,
        }


class StudyFilterActiveQueryService(StudyFilterQueryService):
    key = "active"
    label = _("Active")

    def apply(self, queryset):
        return queryset.filter(deleted=False, is_active=True)


class StudyFilterInactiveQueryService(StudyFilterQueryService):
    key = "inactive"
    label = _("Inactive")

    def apply(self, queryset):
        return queryset.filter(deleted=False, is_active=False)
