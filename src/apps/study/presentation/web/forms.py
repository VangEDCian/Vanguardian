from django import forms
from django.utils.translation import gettext_lazy as _


class StudyForm(forms.Form):
    code = forms.CharField(
        max_length=64,
        label=_("Study Code"),
        widget=forms.TextInput(attrs={"placeholder": _("e.g. STUDY-001")}),
    )
    name = forms.CharField(
        max_length=255,
        label=_("Study Name"),
        widget=forms.TextInput(attrs={"placeholder": _("e.g. REACT-AF Phase II")}),
    )
    sponsor = forms.CharField(
        max_length=255,
        label=_("Sponsor"),
        widget=forms.TextInput(attrs={"placeholder": _("e.g. Acme Pharma")}),
    )
    start_date = forms.DateField(
        required=False,
        label=_("Start Date"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_date = forms.DateField(
        required=False,
        label=_("End Date"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    description = forms.CharField(
        required=False,
        label=_("Description"),
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": _("Enter study description...")}),
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Active"),
    )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date and end_date < start_date:
            self.add_error("end_date", _("End date must be on or after start date."))
        return cleaned_data
