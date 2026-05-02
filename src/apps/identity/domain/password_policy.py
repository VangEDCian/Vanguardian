import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class PasswordPolicyContext:
    username: str = ""
    email: str = ""
    first_name: str = ""
    last_name: str = ""
    display_name: str = ""
    system_name: str = "Vanguardian"

    @classmethod
    def from_user(cls, user, *, system_name="Vanguardian"):
        if user is None:
            return cls(system_name=system_name)

        return cls(
            username=(getattr(user, "get_username", lambda: "")() or "").strip(),
            email=(getattr(user, "email", "") or "").strip(),
            first_name=(getattr(user, "first_name", "") or "").strip(),
            last_name=(getattr(user, "last_name", "") or "").strip(),
            display_name=(getattr(user, "display_name", "") or "").strip(),
            system_name=system_name,
        )


@dataclass(frozen=True)
class PasswordPolicyViolation:
    code: str
    message: str


class PasswordPolicy:
    minimum_length = 12
    requires_periodic_rotation = False
    requirement_messages = (
        "At least 12 characters",
        "Must include uppercase and lowercase letters",
        "Must include at least one digit",
        "Must include at least one special character",
        "Must not be common, easy to guess, exposed, or related to your username, email, or system name",
    )

    _common_passwords = frozenset(
        {
            "123456",
            "123456789",
            "1234567890",
            "111111",
            "000000",
            "qwerty",
            "qwerty123",
            "abc123",
            "password",
            "password1",
            "password123",
            "passw0rd",
            "admin",
            "admin123",
            "administrator",
            "letmein",
            "welcome",
            "welcome1",
            "iloveyou",
            "monkey",
            "dragon",
            "football",
            "baseball",
            "starwars",
            "trustno1",
            "changeme",
            "default",
            "secret",
            "vanguardian",
            "vanguardian123",
        }
    )
    _special_character_pattern = re.compile(r"[^A-Za-z0-9]")

    def validate(self, password, *, context=None):
        password = password or ""
        context = context or PasswordPolicyContext()
        violations = []

        if len(password) < self.minimum_length:
            violations.append(
                PasswordPolicyViolation(
                    code="password_too_short",
                    message=f"Password must contain at least {self.minimum_length} characters.",
                )
            )

        if not any(character.isupper() for character in password):
            violations.append(
                PasswordPolicyViolation(
                    code="password_missing_uppercase",
                    message="Password must include at least one uppercase letter.",
                )
            )

        if not any(character.islower() for character in password):
            violations.append(
                PasswordPolicyViolation(
                    code="password_missing_lowercase",
                    message="Password must include at least one lowercase letter.",
                )
            )

        if not any(character.isdigit() for character in password):
            violations.append(
                PasswordPolicyViolation(
                    code="password_missing_digit",
                    message="Password must include at least one digit.",
                )
            )

        if not self._special_character_pattern.search(password):
            violations.append(
                PasswordPolicyViolation(
                    code="password_missing_special",
                    message="Password must include at least one special character.",
                )
            )

        if self._is_common_or_exposed(password):
            violations.append(
                PasswordPolicyViolation(
                    code="password_common_or_exposed",
                    message="Password is too common, easy to guess, or known to be exposed.",
                )
            )

        if self._contains_contextual_information(password, context=context):
            violations.append(
                PasswordPolicyViolation(
                    code="password_contains_context",
                    message="Password must not contain your username, email, name, or the system name.",
                )
            )

        return violations

    def is_valid(self, password, *, context=None):
        return not self.validate(password, context=context)

    def should_rotate_due_to_compromise(self, *, suspected_compromise=False):
        return bool(suspected_compromise)

    def _is_common_or_exposed(self, password):
        normalized = _normalize_secret(password)
        if normalized in self._common_passwords:
            return True

        stripped = re.sub(r"[^a-z0-9]", "", normalized)
        if stripped in self._common_passwords:
            return True

        return self._has_simple_sequence(stripped)

    def _contains_contextual_information(self, password, *, context):
        normalized_password = _normalize_secret(password)
        comparable_password = re.sub(r"[^a-z0-9]", "", normalized_password)

        for token in _context_tokens(context):
            normalized_token = _normalize_secret(token)
            comparable_token = re.sub(r"[^a-z0-9]", "", normalized_token)
            if len(comparable_token) < 4:
                continue
            if comparable_token in comparable_password:
                return True

        return False

    @staticmethod
    def _has_simple_sequence(value):
        if len(value) < 6:
            return False

        sequences = (
            "abcdefghijklmnopqrstuvwxyz",
            "zyxwvutsrqponmlkjihgfedcba",
            "0123456789",
            "9876543210",
            "qwertyuiop",
            "poiuytrewq",
            "asdfghjkl",
            "lkjhgfdsa",
            "zxcvbnm",
            "mnbvcxz",
        )
        return any(value in sequence for sequence in sequences)


def _context_tokens(context):
    tokens = [
        context.username,
        context.email,
        context.first_name,
        context.last_name,
        context.display_name,
        context.system_name,
    ]

    if context.email and "@" in context.email:
        local_part, domain = context.email.split("@", 1)
        tokens.extend([local_part, domain.split(".", 1)[0]])

    for token in tuple(tokens):
        tokens.extend((token or "").replace(".", " ").replace("_", " ").replace("-", " ").split())

    return tokens


def _normalize_secret(value):
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_value.strip().lower()
