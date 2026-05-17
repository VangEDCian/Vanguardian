from django import forms
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.crf.public import get_crf_template_model
from apps.shared.filters import SharedSearch, SharedTotal

__all__ = [
    "CrfTemplateImportTemplateForm",
    "CrfTemplatesToolbarForm",
]


class CrfTemplateImportTemplateForm(forms.Form):
    import_file = forms.FileField(
        label=_("Import File"),
        allow_empty_file=False,
        widget=forms.ClearableFileInput(
            attrs={
                "accept": ".xlsx,.xls",
            }
        ),
    )

    def clean_import_file(self):
        uploaded_file = self.cleaned_data["import_file"]
        file_name = (uploaded_file.name or "").strip().lower()
        if not file_name.endswith((".xlsx", ".xls")):
            raise forms.ValidationError(_("Only .xlsx and .xls files are supported."))
        return uploaded_file


class CrfTemplatesToolbarForm(SharedSearch, SharedTotal):
    SEARCH_FIELDS = ("code", "version")
    TOTAL_LABEL = _("Total CRF Templates")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bind_total_field()

    @classmethod
    def filter_search(cls, queryset, name, value):
        normalized_value = (value or "").strip()
        if not normalized_value:
            return queryset

        return queryset.filter(
            Q(code__icontains=normalized_value)
            | Q(version__icontains=normalized_value)
            | Q(translations__name__icontains=normalized_value)
        ).distinct()

    class Meta:
        model = get_crf_template_model()
        fields = ("search",)
        toolbar_fields = ("total", "search")
