from django.test import SimpleTestCase

from apps.identity.domain import PasswordPolicy, PasswordPolicyContext


class PasswordPolicyTests(SimpleTestCase):
    def setUp(self):
        self.policy = PasswordPolicy()

    def test_accepts_password_that_satisfies_length_complexity_and_context_rules(self):
        violations = self.policy.validate(
            "R3search!Vault2026",
            context=PasswordPolicyContext(username="coordinator", email="coordinator@example.com"),
        )

        self.assertEqual(violations, [])

    def test_requires_minimum_length_and_all_complexity_classes(self):
        violations = self.policy.validate("short")
        violation_codes = {violation.code for violation in violations}

        self.assertIn("password_too_short", violation_codes)
        self.assertIn("password_missing_uppercase", violation_codes)
        self.assertIn("password_missing_digit", violation_codes)
        self.assertIn("password_missing_special", violation_codes)

    def test_rejects_common_or_exposed_passwords(self):
        violations = self.policy.validate("Password123!")

        self.assertIn("password_common_or_exposed", {violation.code for violation in violations})

    def test_rejects_password_related_to_user_or_system_context(self):
        violations = self.policy.validate(
            "Vanguardian2026!",
            context=PasswordPolicyContext(username="alice", email="alice@example.com", system_name="Vanguardian"),
        )

        self.assertIn("password_contains_context", {violation.code for violation in violations})

    def test_periodic_rotation_is_not_required_without_compromise_suspicion(self):
        self.assertFalse(self.policy.requires_periodic_rotation)
        self.assertFalse(self.policy.should_rotate_due_to_compromise(suspected_compromise=False))
        self.assertTrue(self.policy.should_rotate_due_to_compromise(suspected_compromise=True))
