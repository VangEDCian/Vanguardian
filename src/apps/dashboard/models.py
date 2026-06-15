from django.db import models


class DashboardPermission(models.Model):
    class Meta:
        managed = False
        default_permissions = ()
        verbose_name = "dashboard permission"
        verbose_name_plural = "dashboard permissions"
