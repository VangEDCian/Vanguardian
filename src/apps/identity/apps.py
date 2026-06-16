from django.apps import AppConfig


class IdentityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.identity"
    label = "identity"
    verbose_name = "Identity"

    def ready(self):
        from apps.identity.application.services.default_role_seed import register_default_role_seed

        register_default_role_seed()
