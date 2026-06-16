from django import forms
from django.utils.translation import gettext_lazy as _

__all__ = ["RandomizationImportFileForm"]


class RandomizationImportFileForm(forms.Form):
    import_file = forms.FileField(
        label=_("Import File"),
        allow_empty_file=False,
        widget=forms.ClearableFileInput(
            attrs={
                "accept": ".xlsx,.xls,.csv",
            },
        ),
    )

    def clean_import_file(self):
        uploaded_file = self.cleaned_data["import_file"]
        file_name = (uploaded_file.name or "").strip().lower()
        if not file_name.endswith((".xlsx", ".xls", ".csv")):
            raise forms.ValidationError(
                _("Only .xlsx, .xls, and .csv files are supported."),
            )
        return uploaded_file
