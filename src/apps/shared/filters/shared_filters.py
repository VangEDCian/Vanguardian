__all__ = [
    'SharedFilter',
    'SharedSearch',
    'SharedTotal',
]

import django_filters
from django import forms
from django.db.models import Q

from django.utils.translation import gettext_lazy as _

from apps.shared.widgets import (
    ToolbarFilterSelectWidget,
    ToolbarSearchInputWidget,
    ToolbarTotalWidget,
)


class SharedFilter(django_filters.FilterSet):
    filter = django_filters.ChoiceFilter(
        label=_("Filter"),
        choices=(
            ("active", _("Active")),
            ("inactive", _("Inactive")),
        ),
        empty_label=_("All"),
        method="filter_status",
        widget=ToolbarFilterSelectWidget(
            filter_label=_("Filter:"),
            aria_label=_("Filter records by status"),
        ),
    )

    class Meta:
        abstract = True

    @staticmethod
    def filter_status(queryset, name, value):
        if value in ("active", "true"):
            return queryset.filter(is_active=True)
        if value in ("inactive", "false"):
            return queryset.filter(is_active=False)
        return queryset

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "search" in self.form.fields:
            self.form.fields["search"].widget.attrs.update(
                {"placeholder": _("Enter search value...")},
            )


class SharedSearch(django_filters.FilterSet):
    SEARCH_FIELDS: tuple[str] = ("name",)

    search = django_filters.CharFilter(
        label=_("Search"),
        method='filter_search',
        widget=ToolbarSearchInputWidget(
            attrs={"placeholder": _("Enter search value...")},
            aria_label=_("Search records"),
        ),
    )

    @classmethod
    def filter_search(cls, queryset, name, value):
        if not value:
            return queryset

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


class SharedTotal:
    TOTAL_LABEL = _("Total")

    def bind_total_field(self):
        toolbar_fields = getattr(getattr(self, "Meta", None), "toolbar_fields", ())
        if "total" in toolbar_fields:
            self.form.fields["total"] = forms.CharField(
                required=False,
                widget=ToolbarTotalWidget(
                    total_label=self.TOTAL_LABEL,
                    total_value=self.qs.count(),
                ),
            )
            self._reorder_form_fields(toolbar_fields)

    def _reorder_form_fields(self, toolbar_fields):
        field_mapping = self.form.fields.__class__()
        for field_name in toolbar_fields:
            if field_name in self.form.fields:
                field_mapping[field_name] = self.form.fields[field_name]
        for field_name, field in self.form.fields.items():
            if field_name not in field_mapping:
                field_mapping[field_name] = field
        self.form.fields = field_mapping
