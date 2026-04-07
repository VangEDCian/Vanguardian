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
        required=False,
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
        max_length=255,
        required=False,
        label=_("Description"),
        widget=forms.TextInput(attrs={"placeholder": _("Enter study description...")}),
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


class SiteForm(forms.Form):
    code = forms.CharField(
        max_length=64,
        label=_("Site Code"),
        widget=forms.TextInput(attrs={"placeholder": _("e.g. SITE-001")}),
    )
    name = forms.CharField(
        max_length=255,
        label=_("Site Name"),
        widget=forms.TextInput(attrs={"placeholder": _("e.g. City Medical Center")}),
    )
    investigator = forms.CharField(
        max_length=255,
        required=False,
        label=_("Investigator"),
        widget=forms.TextInput(attrs={"placeholder": _("e.g. Dr. Jane Doe")}),
    )
    study_id = forms.ChoiceField(
        label=_("Study"),
        choices=(),
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Active"),
    )

    def __init__(self, *args, study_choices=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["study_id"].choices = [
            (str(study_id), study_label) for study_id, study_label in study_choices
        ]

    def clean_study_id(self):
        return int(self.cleaned_data["study_id"])


class SiteMembershipForm(forms.Form):
    user_id = forms.ChoiceField(
        label=_("User"),
        choices=(),
    )

    def __init__(self, *args, user_choices=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user_id"].choices = [
            (str(uid), label) for uid, label in user_choices
        ]

    def clean_user_id(self):
        return int(self.cleaned_data["user_id"])
