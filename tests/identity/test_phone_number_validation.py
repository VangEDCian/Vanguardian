from django.test import SimpleTestCase

from apps.identity.application.validators import (
    PhoneNumberValidationError,
    PhoneNumberValidator,
)
from apps.identity.presentation.web.forms import (
    CurrentUserProfileForm,
    IdentityUserCreateForm,
    IdentityUserDetailForm,
)


class PhoneNumberValidatorTests(SimpleTestCase):
    def test_normalizes_valid_vietnamese_phone_number(self):
        validator = PhoneNumberValidator()

        normalized_phone_number = validator.validate("0912345678")

        self.assertEqual(normalized_phone_number, "+84912345678")

    def test_rejects_non_vietnamese_phone_number(self):
        validator = PhoneNumberValidator()

        with self.assertRaises(PhoneNumberValidationError):
            validator.validate("+14155552671")


class IdentityPhoneNumberFormValidationTests(SimpleTestCase):
    def test_user_create_form_rejects_invalid_phone_number(self):
        form = IdentityUserCreateForm(
            data={
                "username": "new-user",
                "password": "R3search!Vault2026",
                "confirm_password": "R3search!Vault2026",
                "phone_number": "123",
            },
            role_choices=(("user", "User"),),
            permission_group_choices=(),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("phone_number", form.errors)

    def test_user_detail_form_rejects_invalid_phone_number(self):
        form = IdentityUserDetailForm(
            data={"phone_number": "abcdef"},
            role_choices=(("user", "User"),),
            permission_group_choices=(),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("phone_number", form.errors)

    def test_profile_form_rejects_invalid_phone_number(self):
        form = CurrentUserProfileForm(
            data={"phone_number": "0"},
            user=None,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("phone_number", form.errors)
