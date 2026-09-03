from django.db import models


class Study(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    sponsor = models.CharField(max_length=255, null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    description = models.CharField(max_length=255, default="")
    is_active = models.BooleanField(default=True)
    subject_identifier_mode = models.CharField(
        max_length=48,
        choices=(
            ("generated_at_screening", "generated_at_screening"),
            ("generated_at_enrollment", "generated_at_enrollment"),
            (
                "copy_randomization_at_randomization",
                "copy_randomization_at_randomization",
            ),
            ("external", "external"),
        ),
        default="generated_at_enrollment",
    )
    screening_identifier_mode = models.CharField(
        max_length=16,
        choices=(
            ("generated", "generated"),
            ("external", "external"),
            ("disabled", "disabled"),
        ),
        default="generated",
    )
    subject_code_pattern = models.CharField(
        max_length=128,
        default="{study_code}-{sequence:03d}",
    )
    screening_code_pattern = models.CharField(
        max_length=128,
        default="{study_code}-S{sequence:03d}",
    )
    subject_code_uniqueness_scope = models.CharField(
        max_length=16,
        choices=(
            ("study_site", "study_site"),
            ("study", "study"),
        ),
        default="study_site",
    )
    lock_subject_code_after_assignment = models.BooleanField(default=True)
    crf_page_lifecycle_configured = models.BooleanField(default=False)

    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "study_study"
        managed = True
        default_permissions = ()
        indexes = [
            models.Index(fields=["code"], name="study_code_idx"),
            models.Index(fields=["deleted"], name="study_deleted_idx"),
            models.Index(fields=["created_by_id"], name="study_created_by_idx"),
            models.Index(fields=["deleted", "created_by_id"], name="study_deleted_creator_idx"),
            models.Index(fields=["deleted", "is_active"], name="study_deleted_active_idx"),
            models.Index(fields=["deleted", "start_date"], name="study_deleted_start_idx"),
            models.Index(fields=["deleted", "end_date"], name="study_deleted_end_idx"),
        ]
        verbose_name = "study"
        verbose_name_plural = "studies"
        ordering = ("id",)
