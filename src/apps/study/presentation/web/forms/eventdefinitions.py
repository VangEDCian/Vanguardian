from django import forms
from django.utils.translation import gettext_lazy as _

from apps.shared.filters import SharedSearch, SharedTotal
from apps.study.infrastructure.persistence.models import EventDefinition

__all__ = [
    "EventDefinitionImportTemplateForm",
    "EventDefinitionsToolbarForm",
    "FactMappingImportTemplateForm",
]


class EventDefinitionImportTemplateForm(forms.Form):
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


class FactMappingImportTemplateForm(forms.Form):
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


class EventDefinitionsToolbarForm(SharedSearch, SharedTotal):
    SEARCH_FIELDS = (
        "study_version",
        "code",
        "name",
        "description",
        "event_type",
        "timing_mode",
        "event_category",
        "execution_mode",
    )
    TOTAL_LABEL = _("Total Event Definitions")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bind_total_field()

    class Meta:
        model = EventDefinition
        fields = ("search",)
        toolbar_fields = ("total", "search")
