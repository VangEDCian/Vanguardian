__all__ = [
    "SiteForm",
    "SiteMembershipForm",
    "SitesToolbarForm",
]

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.shared.filters import SharedFilter, SharedSearch, SharedTotal
from apps.study.infrastructure.persistence.models import Site


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

    def __init__(
        self, *args, study_choices=(), fixed_study_id=None, fixed_code=None, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.fixed_study_id = fixed_study_id
        self.fixed_code = fixed_code
        self.fields["study_id"].choices = [
            (str(study_id), study_label) for study_id, study_label in study_choices
        ]
        if self.fixed_study_id is not None:
            self.fields["study_id"].required = False
            self.fields["study_id"].initial = str(self.fixed_study_id)
        if self.fixed_code is not None:
            self.fields["code"].required = False
            self.fields["code"].initial = self.fixed_code

    def clean_code(self):
        if self.fixed_code is not None:
            return self.fixed_code
        return self.cleaned_data["code"].strip()

    def clean_study_id(self):
        if self.fixed_study_id is not None:
            return int(self.fixed_study_id)
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


class SitesToolbarForm(SharedFilter, SharedSearch, SharedTotal):
    SEARCH_FIELDS = ("name", "code")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bind_total_field()

    class Meta:
        model = Site
        fields = ("filter", "search")
        toolbar_fields = ("filter", "total", "search")
