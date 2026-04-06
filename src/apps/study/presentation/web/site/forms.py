from django import forms
from django.utils.translation import gettext_lazy as _


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


