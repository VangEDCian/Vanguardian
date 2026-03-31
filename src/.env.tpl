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