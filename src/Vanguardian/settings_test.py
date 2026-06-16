from .settings import *  # noqa: F403

DEBUG = False
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SEARCH_ENGINE_INDEXING_ENABLED = False

ALLOWED_HOSTS = list(ALLOWED_HOSTS) + [  # noqa: F405
    "testserver",
    "app",
    "mariadb",
    "127.0.0.1",
    "localhost",
]

CSRF_TRUSTED_ORIGINS = list(CSRF_TRUSTED_ORIGINS)  # noqa: F405

DATABASE_DISABLE_CONSTRAINTS = False
DATABASE_DISABLE_FOREIGN_KEY_CONSTRAINTS = False

default_database = DATABASES["default"]  # noqa: F405
default_database.setdefault("TEST", {})
default_database["TEST"]["NAME"] = env(  # noqa: F405
    "TEST_DATABASE_NAME",
    cast=str,
    default="test_vanguardian",
)
if default_database.get("ENGINE") == "Vanguardian.db.backends.mysql_no_constraints":
    default_database["ENGINE"] = "django.db.backends.mysql"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "vanguardian-test-cache",
    }
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
