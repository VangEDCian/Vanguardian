from django.core.cache import caches
from django.test import RequestFactory, SimpleTestCase, override_settings

from apps.identity.infrastructure.auth.rate_limit import IdentityLoginRateLimiter


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "identity-login-rate-limit-tests",
        }
    },
    IDENTITY_LOGIN_RATE_LIMIT_MAX_ATTEMPTS=2,
    IDENTITY_LOGIN_RATE_LIMIT_WINDOW_SECONDS=60,
    IDENTITY_LOGIN_RATE_LIMIT_LOCKOUT_SECONDS=60,
)
class IdentityLoginRateLimiterTests(SimpleTestCase):
    def setUp(self):
        caches["default"].clear()
        self.factory = RequestFactory()
        self.limiter = IdentityLoginRateLimiter()
        self.request = self.factory.post("/itsnotasignin/", REMOTE_ADDR="127.0.0.1")

    def tearDown(self):
        caches["default"].clear()

    def test_locks_identifier_after_configured_failed_attempts(self):
        self.assertFalse(self.limiter.is_limited(self.request, "user@example.com"))

        self.limiter.record_failure(self.request, "user@example.com")
        self.assertFalse(self.limiter.is_limited(self.request, "user@example.com"))

        self.limiter.record_failure(self.request, "user@example.com")
        self.assertTrue(self.limiter.is_limited(self.request, "user@example.com"))

    def test_reset_clears_lockout_state(self):
        self.limiter.record_failure(self.request, "user@example.com")
        self.limiter.record_failure(self.request, "user@example.com")

        self.limiter.reset(self.request, "user@example.com")

        self.assertFalse(self.limiter.is_limited(self.request, "user@example.com"))
