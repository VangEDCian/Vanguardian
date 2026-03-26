from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm
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
