from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.identity.domain import PasswordPolicy, PasswordPolicyContext


class PasswordPolicyValidator:
    policy_class = PasswordPolicy

    def __init__(self):
        self.policy = self.policy_class()

    def validate(self, password, user=None):
        violations = self.policy.validate(
            password,
            context=PasswordPolicyContext.from_user(user),
        )
        if violations:
            raise ValidationError(
                [_(violation.message) for violation in violations],
                code="password_policy_violation",
            )

    def get_help_text(self):
        return _("Password must satisfy the system password policy.")
