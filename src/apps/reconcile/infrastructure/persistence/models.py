from django.db import models
from django.utils.translation import gettext_lazy as _


class ReconcileDataQueryStatusChoices(models.TextChoices):
    OPEN = "open", _("Open")
    CLOSED = "closed", _("Closed")


class ReconcileDataQuerySourceChoices(models.TextChoices):
    MANUAL = "manual", _("Manual")
    SYSTEM = "system", _("System")
    IMPORT = "import", _("Import")


class ReconcileDataQuery(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    status = models.CharField(
        max_length=16,
        choices=ReconcileDataQueryStatusChoices.choices,
    )
    source = models.CharField(
        max_length=16,
        choices=ReconcileDataQuerySourceChoices.choices,
    )
    question_text = models.TextField()
    resolution_note = models.CharField(max_length=255, null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    page_state = models.ForeignKey(
        "datacapture.DataCapturePageState",
        on_delete=models.DO_NOTHING,
        db_column="page_state_id",
        related_name="reconcile_data_queries",
    )
    field_template = models.ForeignKey(
        "crf.CrfFieldTemplate",
        on_delete=models.DO_NOTHING,
        db_column="field_template_id",
        related_name="reconcile_data_queries",
        null=True,
        blank=True,
    )
    validation_rule = models.ForeignKey(
        "crf.CrfFieldValidationRule",
        on_delete=models.DO_NOTHING,
        db_column="validation_rule_id",
        related_name="reconcile_data_queries",
        null=True,
        blank=True,
    )
    assigned_to_id = models.BigIntegerField(null=True, blank=True)
    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "reconcile_dataquery"
        managed = False
        default_permissions = ()
        verbose_name = "reconcile data query"
        verbose_name_plural = "reconcile data queries"


__all__ = [
    "ReconcileDataQuery",
    "ReconcileDataQuerySourceChoices",
    "ReconcileDataQueryStatusChoices",
]

