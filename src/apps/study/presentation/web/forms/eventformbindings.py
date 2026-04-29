from django import forms
from django.utils.translation import gettext_lazy as _


class EventFormBindingImportTemplateForm(forms.Form):
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
