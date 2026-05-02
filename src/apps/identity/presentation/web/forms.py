from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.identity.application.validators import (
    PhoneNumberValidationError,
    PhoneNumberValidator,
)
from apps.identity.domain import PasswordPolicy, PasswordPolicyContext
from apps.identity.infrastructure.auth.rate_limit import IdentityLoginRateLimiter
from apps.identity.models import User


class StyledAuthenticationForm(AuthenticationForm):
    login_rate_limiter_class = IdentityLoginRateLimiter

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_rate_limiter = self.login_rate_limiter_class()
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

    def clean(self):
        identifier = (self.cleaned_data.get("username") or "").strip()
        if identifier and self.login_rate_limiter.is_limited(self.request, identifier):
            raise ValidationError(
                _("Too many failed sign-in attempts. Please try again later."),
                code="too_many_login_attempts",
            )

        try:
            return super().clean()
        except ValidationError:
            self.login_rate_limiter.record_failure(self.request, identifier)
            raise

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        self.login_rate_limiter.reset(
            self.request,
            (self.cleaned_data.get("username") or user.get_username() or "").strip(),
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
    password_requirements = tuple(_(message) for message in PasswordPolicy.requirement_messages)

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
    studies = forms.MultipleChoiceField(required=False)
    sites = forms.MultipleChoiceField(required=False)
    new_password = forms.CharField(max_length=128, required=False)
    confirm_password = forms.CharField(max_length=128, required=False)

    def __init__(self, *args, role_choices=(), permission_group_choices=(), study_choices=(), site_choices=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.phone_number_validator = PhoneNumberValidator()
        self.fields["role"].choices = role_choices
        self.fields["permission_groups"].choices = permission_group_choices
        self.fields["studies"].choices = study_choices
        self.fields["sites"].choices = site_choices

    def clean_phone_number(self):
        phone_number = (self.cleaned_data.get("phone_number") or "").strip()
        if not phone_number:
            return ""

        try:
            return self.phone_number_validator.validate(phone_number)
        except PhoneNumberValidationError as exc:
            raise ValidationError(_(str(exc))) from exc

    def clean(self):
        cleaned_data = super().clean()
        new_password = (cleaned_data.get("new_password") or "").strip()
        confirm_password = (cleaned_data.get("confirm_password") or "").strip()

        if new_password:
            if new_password != confirm_password:
                self.add_error("confirm_password", _("Passwords do not match."))
            else:
                self._add_password_policy_errors("new_password", new_password)

        cleaned_data["new_password"] = new_password or None
        cleaned_data["studies"] = _normalize_multi_values(cleaned_data.get("studies"))
        cleaned_data["sites"] = _normalize_multi_values(cleaned_data.get("sites"))
        return cleaned_data

    def _add_password_policy_errors(self, field_name, password):
        for violation in PasswordPolicy().validate(password):
            self.add_error(field_name, _(violation.message))


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
    studies = forms.MultipleChoiceField(required=False)
    sites = forms.MultipleChoiceField(required=False)

    def __init__(self, *args, role_choices=(), permission_group_choices=(), study_choices=(), site_choices=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.phone_number_validator = PhoneNumberValidator()
        self.fields["role"].choices = role_choices
        self.fields["permission_groups"].choices = permission_group_choices
        self.fields["studies"].choices = study_choices
        self.fields["sites"].choices = site_choices

    def clean_username(self):
        return (self.cleaned_data.get("username") or "").strip()

    def clean_phone_number(self):
        phone_number = (self.cleaned_data.get("phone_number") or "").strip()
        if not phone_number:
            return ""

        try:
            return self.phone_number_validator.validate(phone_number)
        except PhoneNumberValidationError as exc:
            raise ValidationError(_(str(exc))) from exc

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password") or ""
        confirm_password = cleaned_data.get("confirm_password") or ""

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", _("Passwords do not match."))

        if password:
            self._add_password_policy_errors(
                "password",
                password,
                context=PasswordPolicyContext(
                    username=cleaned_data.get("username") or "",
                    email=cleaned_data.get("email") or "",
                    first_name=cleaned_data.get("first_name") or "",
                    last_name=cleaned_data.get("last_name") or "",
                    display_name=" ".join(
                        value
                        for value in (
                            cleaned_data.get("first_name") or "",
                            cleaned_data.get("last_name") or "",
                        )
                        if value
                    ),
                ),
            )

        cleaned_data["studies"] = _normalize_multi_values(cleaned_data.get("studies"))
        cleaned_data["sites"] = _normalize_multi_values(cleaned_data.get("sites"))
        return cleaned_data

    def _add_password_policy_errors(self, field_name, password, *, context):
        for violation in PasswordPolicy().validate(password, context=context):
            self.add_error(field_name, _(violation.message))


class IdentityUserChangePasswordForm(forms.Form):
    password_requirements = tuple(_(message) for message in PasswordPolicy.requirement_messages)
    new_password = forms.CharField(min_length=PasswordPolicy.minimum_length, max_length=100)
    retype_new_password = forms.CharField(min_length=PasswordPolicy.minimum_length, max_length=100)

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_password(self):
        new_password = (self.cleaned_data.get("new_password") or "").strip()
        if not new_password:
            raise ValidationError(_("Please enter a new password."))
        _raise_password_policy_validation_error(new_password, user=self.user)
        return new_password

    def clean_retype_new_password(self):
        retype_new_password = (self.cleaned_data.get("retype_new_password") or "").strip()
        if not retype_new_password:
            raise ValidationError(_("Please confirm your new password."))
        return retype_new_password

    def clean(self):
        cleaned_data: dict | None = super().clean()

        if cleaned_data:
            new_password = cleaned_data.get('new_password', None)
            retype_new_password = cleaned_data.get('retype_new_password', None)

            if new_password and retype_new_password:
                if new_password != retype_new_password:
                    raise ValidationError(_("The new password and confirmation do not match."))

        return cleaned_data


class CurrentUserProfileForm(forms.Form):
    display_name = forms.CharField(max_length=255, required=False)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)
    phone_number = forms.CharField(max_length=32, required=False)

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.phone_number_validator = PhoneNumberValidator()
        self.fields["display_name"].widget.attrs.update(
            {
                "autocomplete": "name",
                "class": "admin-account-field__input",
                "placeholder": _("Enter display name"),
            }
        )
        self.fields["first_name"].widget.attrs.update(
            {
                "autocomplete": "given-name",
                "class": "admin-account-field__input",
                "placeholder": _("Enter first name"),
            }
        )
        self.fields["last_name"].widget.attrs.update(
            {
                "autocomplete": "family-name",
                "class": "admin-account-field__input",
                "placeholder": _("Enter last name"),
            }
        )
        self.fields["email"].widget.attrs.update(
            {
                "autocomplete": "email",
                "class": "admin-account-field__input",
                "placeholder": "name@example.com",
            }
        )
        self.fields["phone_number"].widget.attrs.update(
            {
                "autocomplete": "tel",
                "class": "admin-account-field__input",
                "placeholder": _("Enter phone number"),
            }
        )

    def clean_display_name(self):
        return (self.cleaned_data.get("display_name") or "").strip()

    def clean_first_name(self):
        return (self.cleaned_data.get("first_name") or "").strip()

    def clean_last_name(self):
        return (self.cleaned_data.get("last_name") or "").strip()

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip()
        if email and self._user_exists_with_value("email", email):
            raise ValidationError(_("This email address is already in use."))
        return email

    def clean_phone_number(self):
        phone_number = (self.cleaned_data.get("phone_number") or "").strip()
        if not phone_number:
            return ""

        try:
            normalized_phone_number = self.phone_number_validator.validate(phone_number)
        except PhoneNumberValidationError as exc:
            raise ValidationError(_(str(exc))) from exc

        if self._user_exists_with_value("phone_number", normalized_phone_number):
            raise ValidationError(_("This phone number is already in use."))
        return normalized_phone_number

    def _user_exists_with_value(self, field_name, value):
        queryset = User.objects.filter(**{f"{field_name}__iexact": value})
        if self.user and getattr(self.user, "pk", None):
            queryset = queryset.exclude(pk=self.user.pk)
        return queryset.exists()


class CurrentUserChangePasswordForm(forms.Form):
    password_requirements = tuple(_(message) for message in PasswordPolicy.requirement_messages)
    current_password = forms.CharField(max_length=128)
    new_password = forms.CharField(max_length=128)
    confirm_password = forms.CharField(max_length=128)

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["current_password"].widget = forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "class": "admin-account-field__input admin-account-field__input--password",
                "placeholder": _("Enter current password"),
            }
        )
        self.fields["new_password"].widget = forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "class": "admin-account-field__input admin-account-field__input--password",
                "placeholder": _("Enter new password"),
            }
        )
        self.fields["confirm_password"].widget = forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "class": "admin-account-field__input admin-account-field__input--password",
                "placeholder": _("Confirm new password"),
            }
        )

    def clean_current_password(self):
        current_password = self.cleaned_data.get("current_password") or ""
        if not self.user or not self.user.check_password(current_password):
            raise ValidationError(_("Current password is incorrect."))
        return current_password

    def clean_new_password(self):
        new_password = self.cleaned_data.get("new_password") or ""
        _raise_password_policy_validation_error(new_password, user=self.user)
        return new_password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password") or ""
        confirm_password = cleaned_data.get("confirm_password") or ""

        if new_password and confirm_password and new_password != confirm_password:
            self.add_error("confirm_password", _("Passwords do not match."))

        return cleaned_data


def _raise_password_policy_validation_error(password, *, user=None):
    violations = PasswordPolicy().validate(
        password,
        context=PasswordPolicyContext.from_user(user),
    )
    if violations:
        raise ValidationError([_(violation.message) for violation in violations])


def _normalize_multi_values(values):
    normalized_values = []
    seen_values = set()
    for value in values or ():
        normalized_value = str(value).strip()
        if not normalized_value or normalized_value in seen_values:
            continue
        seen_values.add(normalized_value)
        normalized_values.append(normalized_value)
    return normalized_values
