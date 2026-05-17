from django.apps import AppConfig


class DatacaptureConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.datacapture"
    label = "datacapture"
    verbose_name = "Datacapture"
