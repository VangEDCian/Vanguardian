from django.contrib.auth.apps import AuthConfig


class ManualPermissionAuthConfig(AuthConfig):
    """
    Backward-compatible alias for django.contrib.auth AppConfig.
    Automatic permission creation remains enabled.
    """

    # Keep explicit name/label to register django.contrib.auth correctly.
    name = "django.contrib.auth"
    label = "auth"
