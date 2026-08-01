from django import forms
from django.utils.translation import gettext_lazy as _

__all__ = [
    "Nng31MasterListApprovalForm",
    "Nng31MasterListImportFileForm",
    "RandomizationImportFileForm",
]


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


class Nng31MasterListImportFileForm(forms.Form):
    master_list_version = forms.CharField(
        label=_("Master-list Version"),
        max_length=64,
    )
    import_file = forms.FileField(
        label=_("Import File"),
        allow_empty_file=False,
        widget=forms.ClearableFileInput(attrs={"accept": ".xlsx"}),
    )

    def clean_import_file(self):
        uploaded_file = self.cleaned_data["import_file"]
        if not str(uploaded_file.name or "").strip().lower().endswith(".xlsx"):
            raise forms.ValidationError(_("Only .xlsx files are supported."))
        return uploaded_file


class Nng31MasterListApprovalForm(forms.Form):
    scheme_id = forms.IntegerField(min_value=1)
    expected_checksum = forms.CharField(max_length=64, min_length=64)
