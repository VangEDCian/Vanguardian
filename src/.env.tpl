# -----------------------------------------------------------------------------
# Django core settings (used in src/Vanguardian/settings.py)
# -----------------------------------------------------------------------------
SECRET_KEY=django-insecure-secret
DEBUG=
ALLOWED_HOSTS=
CSRF_TRUSTED_ORIGINS=
TZ=

# -----------------------------------------------------------------------------
# Database and cache URLs used by django-environ
# -----------------------------------------------------------------------------
# Source runs on host machine (connect to docker services via published ports)
DATABASE_URL=
CACHE_URL=

# If source runs inside the same docker network, switch to service DNS names:

# -----------------------------------------------------------------------------
# SMTP settings (password reset email via aiosmtplib backend)
# -----------------------------------------------------------------------------
EMAIL_BACKEND=
EMAIL_HOST=
EMAIL_PORT=
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=
EMAIL_USE_STARTTLS=
EMAIL_TIMEOUT=
DEFAULT_FROM_EMAIL=


PASSWORD_RESET_TIMEOUT=

IDENTITY_LOGIN_RATE_LIMIT_MAX_ATTEMPTS=
IDENTITY_LOGIN_RATE_LIMIT_WINDOW_SECONDS=
IDENTITY_LOGIN_RATE_LIMIT_LOCKOUT_SECONDS=

# -----------------------------------------------------------------------------
# Sonic search settings
# -----------------------------------------------------------------------------
SONIC_ENABLED=
SONIC_HOST=
SONIC_PORT=
SONIC_PASSWORD=
SONIC_COLLECTION=
SONIC_BUCKET_STUDIES=
SONIC_BUCKET_SITES=
SONIC_LANGUAGE=
SONIC_SEARCH_LIMIT=
