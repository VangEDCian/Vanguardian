from django import forms
from django.utils.translation import gettext_lazy as _

from apps.shared.filters import SharedSearch, SharedTotal
from apps.subject.models import Subject

__all__ = ["SubjectEventInstanceFileImportForm", "SubjectsToolbarForm"]


class SubjectsToolbarForm(SharedSearch, SharedTotal):
    SEARCH_FIELDS = ("subject_code", "screening_code")
    TOTAL_LABEL = _("Total Subjects")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bind_total_field()

    class Meta:
        model = Subject
        fields = ("search",)
        toolbar_fields = ("total", "search")


class SubjectEventInstanceFileImportForm(forms.Form):
    import_file = forms.FileField(
        label=_("Import File"),
    )

    def clean_import_file(self):
        uploaded_file = self.cleaned_data["import_file"]
        if not uploaded_file:
            raise forms.ValidationError(_("Please choose a file to import."))
        if uploaded_file.size <= 0:
            raise forms.ValidationError(_("Uploaded file is empty."))
        return uploaded_file
