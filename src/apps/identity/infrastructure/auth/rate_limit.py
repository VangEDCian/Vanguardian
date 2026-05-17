import hashlib

from django.conf import settings
from django.core.cache import cache


class IdentityLoginRateLimiter:
    max_attempts = 5
    window_seconds = 15 * 60
    lockout_seconds = 15 * 60

    def is_limited(self, request, identifier):
        key = self._lockout_key(request, identifier)
        return bool(cache.get(key))

    def record_failure(self, request, identifier):
        if not identifier:
            return

        attempts_key = self._attempts_key(request, identifier)
        attempts = int(cache.get(attempts_key) or 0) + 1
        cache.set(attempts_key, attempts, self._setting("IDENTITY_LOGIN_RATE_LIMIT_WINDOW_SECONDS", self.window_seconds))

        max_attempts = self._setting("IDENTITY_LOGIN_RATE_LIMIT_MAX_ATTEMPTS", self.max_attempts)
        if attempts >= max_attempts:
            cache.set(
                self._lockout_key(request, identifier),
                True,
                self._setting("IDENTITY_LOGIN_RATE_LIMIT_LOCKOUT_SECONDS", self.lockout_seconds),
            )

    def reset(self, request, identifier):
        if not identifier:
            return

        cache.delete(self._attempts_key(request, identifier))
        cache.delete(self._lockout_key(request, identifier))

    def _attempts_key(self, request, identifier):
        return f"identity:login-rate-limit:attempts:{self._cache_key_material(request, identifier)}"

    def _lockout_key(self, request, identifier):
        return f"identity:login-rate-limit:lockout:{self._cache_key_material(request, identifier)}"

    def _cache_key_material(self, request, identifier):
        normalized_identifier = (identifier or "").strip().lower()
        ip_address = self._client_ip(request)
        digest = hashlib.sha256(f"{normalized_identifier}|{ip_address}".encode("utf-8")).hexdigest()
        return digest

    @staticmethod
    def _client_ip(request):
        if request is None:
            return ""
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded_for:
            return forwarded_for.split(",", 1)[0].strip()
        return request.META.get("REMOTE_ADDR", "") or ""

    @staticmethod
    def _setting(name, default):
        return int(getattr(settings, name, default))
