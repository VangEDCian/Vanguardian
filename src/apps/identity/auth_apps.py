from django.contrib.auth.apps import AuthConfig
from django.contrib.auth.management import create_permissions
from django.db.models.signals import post_migrate


class ManualPermissionAuthConfig(AuthConfig):
    """
    Keep django-auth's user/group/permission runtime, but stop automatic
    permission creation so the project can own permission provisioning.
    """

    def ready(self):
        super().ready()
        post_migrate.disconnect(
            create_permissions,
            dispatch_uid="django.contrib.auth.management.create_permissions",
        )

