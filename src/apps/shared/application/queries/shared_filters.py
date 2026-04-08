__all__ = [
    'SharedIsActiveFilter',
    'SharedSearchFilter',
]

import django_filters
from django.db.models import Q

from django.utils.translation import gettext_lazy as _


class SharedIsActiveFilter(django_filters.FilterSet):
    is_active = django_filters.TypedChoiceFilter(
        label=_("STATUS"),
        choices=(
            ("", _("All statuses")),
            ("true", _("Active")),
            ("false", _("Inactive")),
        ),
        coerce=lambda v: {"true": True, "false": False}.get(v, None),
        empty_value="",
    )

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form.fields['search'].widget.attrs.update({"placeholder": _("Enter search value...")})


class SharedSearchFilter(django_filters.FilterSet):
    SEARCH_FIELDS: tuple[str] = ("name",)

    search = django_filters.CharFilter(
        label=_("Search"),
        method='filter_search',
    )

    @classmethod
    def filter_search(cls, queryset, name, value):
        if not value:
            return queryset

        # Adjust this list to your real model fields
        candidate_fields = cls.SEARCH_FIELDS

        model_fields = {f.name for f in queryset.model._meta.get_fields() if hasattr(f, "attname")}
        lookup_fields = [f for f in candidate_fields if f in model_fields]

        if not lookup_fields:
            return queryset

        q_obj = Q()
        for field in lookup_fields:
            q_obj |= Q(**{f"{field}__icontains": value})

        return queryset.filter(q_obj)

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form.fields['search'].widget.attrs.update({"placeholder": _("Enter search value...")})
