from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {
                "placeholder": "Nhập tên đăng nhập",
                "autocomplete": "username",
            }
        )
        self.fields["password"].widget.attrs.update(
            {
                "placeholder": "Nhập mật khẩu",
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
        "Ít nhất 8 ký tự",
        "Bao gồm chữ hoa và chữ thường",
        "Ít nhất một số hoặc ký tự đặc biệt",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].widget.attrs.update(
            {
                "placeholder": "Nhập mật khẩu mới",
                "autocomplete": "new-password",
            }
        )
        self.fields["new_password2"].widget.attrs.update(
            {
                "placeholder": "Nhập lại mật khẩu mới",
                "autocomplete": "new-password",
            }
        )

