from django import forms
from django.utils.translation import gettext_lazy as _


class StudyRoleCreateForm(forms.Form):
    name = forms.CharField(max_length=150, label=_("Role Name"))
    code = forms.CharField(max_length=100, required=False, label=_("Role Code"))
    description = forms.CharField(max_length=255, required=False, label=_("Description"))
    scope_level = forms.ChoiceField(label=_("Scope"))
    permissions = forms.MultipleChoiceField(required=False, label=_("Permissions"))

    def __init__(self, *args, scope_choices=(), permission_choices=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["scope_level"].choices = scope_choices
        self.fields["permissions"].choices = permission_choices
        if not self.is_bound and scope_choices:
            self.initial["scope_level"] = scope_choices[0][0]

    def clean_name(self):
        return self.cleaned_data["name"].strip()

    def clean_code(self):
        return (self.cleaned_data.get("code") or "").strip()

    def clean_description(self):
        return (self.cleaned_data.get("description") or "").strip()

    def role_data(self):
        return {
            "name": self.cleaned_data["name"],
            "code": self.cleaned_data.get("code", ""),
            "description": self.cleaned_data.get("description", ""),
            "scope_level": self.cleaned_data["scope_level"],
            "permission_ids": self.cleaned_data.get("permissions", ()),
        }
