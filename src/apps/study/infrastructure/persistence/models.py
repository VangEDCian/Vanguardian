from django.db import models


class Study(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    sponsor = models.CharField(max_length=255)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(default="")
    is_active = models.BooleanField(default=True)

    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "study_study"
        managed = False
        default_permissions = ()
        permissions = (
            ("view_study_list", "Can view study list"),
            ("view_study_detail", "Can view study detail"),
            ("create_study", "Can create study"),
            ("update_study", "Can update study"),
            ("delete_study", "Can delete study"),
        )
        indexes = [
            models.Index(fields=["deleted", "is_active"], name="study_deleted_active_idx"),
            models.Index(fields=["deleted", "start_date"], name="study_deleted_start_idx"),
            models.Index(fields=["deleted", "end_date"], name="study_deleted_end_idx"),
        ]
        verbose_name = "study"
        verbose_name_plural = "studies"
