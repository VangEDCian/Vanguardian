from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.identity.infrastructure.persistence.models import User


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
    new_password = forms.CharField(max_length=128, required=False)
    confirm_password = forms.CharField(max_length=128, required=False)

    def __init__(self, *args, role_choices=(), permission_group_choices=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = role_choices
        self.fields["permission_groups"].choices = permission_group_choices

    def clean_phone_number(self):
        return (self.cleaned_data.get("phone_number") or "").strip()

    def clean(self):
        cleaned_data = super().clean()
        new_password = (cleaned_data.get("new_password") or "").strip()
        confirm_password = (cleaned_data.get("confirm_password") or "").strip()

        if new_password:
            if new_password != confirm_password:
                self.add_error("confirm_password", _("Passwords do not match."))
            else:
                try:
                    validate_password(new_password)
                except ValidationError as exc:
                    self.add_error("new_password", exc)

        cleaned_data["new_password"] = new_password or None
        return cleaned_data


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


class IdentityUserChangePasswordForm(forms.Form):
    password = forms.CharField(min_length=1, max_length=100)
    new_password = forms.CharField(min_length=8, max_length=100)
    retype_new_password = forms.CharField(min_length=8, max_length=100)

    def clean_password(self):
        password = (self.cleaned_data.get("password") or "").strip()
        if not password:
            raise ValidationError(_("Current password is required."))
        return password

    def clean_new_password(self):
        new_password = (self.cleaned_data.get("new_password") or "").strip()
        if not new_password:
            raise ValidationError(_("Please enter a new password."))
        validate_password(new_password)
        return new_password

    def clean_retype_new_password(self):
        retype_new_password = (self.cleaned_data.get("retype_new_password") or "").strip()
        if not retype_new_password:
            raise ValidationError(_("Please confirm your new password."))
        validate_password(retype_new_password)
        return retype_new_password

    def clean(self):
        cleaned_data: dict | None = super().clean()

        if cleaned_data:
            password = cleaned_data.get('password', "")
            new_password = cleaned_data.get('new_password', None)
            retype_new_password = cleaned_data.get('retype_new_password', None)

            if password and new_password and retype_new_password:
                if new_password != retype_new_password:
                    raise ValidationError(_("The new password and confirmation do not match."))

                if new_password == password:
                    raise ValidationError(_("Your new password must be different from the current password."))

                if not (self.user and self.user.check_password(password)):
                    raise ValidationError(_("Password is incorrect."))

        return cleaned_data

    def __init__(self, user: User = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
