from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = _("Username")
        self.fields["username"].widget.attrs.update(
            {
                "placeholder": _("Enter username"),
                "autocomplete": "username",
            }
        )
        self.fields["password"].widget.attrs.update(
            {
                "placeholder": _("Enter password"),
                "autocomplete": "current-password",
            }
        )


class StyledPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.update(
            {
                "placeholder": "example@email.com",
                "autocomplete": "email",
            }
        )


class StyledSetPasswordForm(SetPasswordForm):
    password_requirements = (
        _("At least 8 characters"),
        _("Must include uppercase and lowercase letters"),
        _("At least one number or special character"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].widget.attrs.update(
            {
                "placeholder": _("Enter new password"),
                "autocomplete": "new-password",
            }
        )
        self.fields["new_password2"].widget.attrs.update(
            {
                "placeholder": _("Confirm new password"),
                "autocomplete": "new-password",
            }
        )


class IdentityUserDetailForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)
    phone_number = forms.CharField(max_length=32, required=False)
    is_active = forms.BooleanField(required=False)
    role = forms.ChoiceField(required=False)
    permission_groups = forms.MultipleChoiceField(required=False)

    def __init__(self, *args, role_choices=(), permission_group_choices=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = role_choices
        self.fields["permission_groups"].choices = permission_group_choices

    def clean_phone_number(self):
        return (self.cleaned_data.get("phone_number") or "").strip()


class IdentityUserCreateForm(forms.Form):
    username = forms.CharField(max_length=150, required=True)
    password = forms.CharField(max_length=128, required=True)
    confirm_password = forms.CharField(max_length=128, required=True)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)
    phone_number = forms.CharField(max_length=32, required=False)
    role = forms.ChoiceField(required=False)
    permission_groups = forms.MultipleChoiceField(required=False)

    def __init__(self, *args, role_choices=(), permission_group_choices=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = role_choices
        self.fields["permission_groups"].choices = permission_group_choices

    def clean_username(self):
        return (self.cleaned_data.get("username") or "").strip()

    def clean_phone_number(self):
        return (self.cleaned_data.get("phone_number") or "").strip()

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password") or ""
        confirm_password = cleaned_data.get("confirm_password") or ""

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", _("Passwords do not match."))

        if password:
            try:
                validate_password(password)
            except ValidationError as exc:
                self.add_error("password", exc)

        return cleaned_data
