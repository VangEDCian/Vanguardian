from django.db import models

from .study import Study


class StudyCrfPageLifecycleStep(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    study = models.ForeignKey(
        Study,
        on_delete=models.CASCADE,
        db_column="study_id",
        related_name="crf_page_lifecycle_steps",
    )
    step_code = models.CharField(max_length=16)
    display_order = models.PositiveSmallIntegerField()
    allowed_role_ids = models.JSONField(default=list)
    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "study_crf_page_lifecycle_step"
        managed = True
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["study", "step_code"],
                name="study_crf_page_lifecycle_step_uniq",
            ),
            models.UniqueConstraint(
                fields=["study", "display_order"],
                name="study_crf_page_lifecycle_order_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["study", "display_order"],
                name="study_crf_pg_lc_order_idx",
            ),
        ]
        ordering = ("display_order", "id")


__all__ = ["StudyCrfPageLifecycleStep"]
