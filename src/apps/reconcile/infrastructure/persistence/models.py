from django.db import models
from django.utils.translation import gettext_lazy as _


class ReconcileDataQueryStatusChoices(models.TextChoices):
    OPEN = "open", _("Open")
    ANSWERED = "answered", _("Answered")
    RESOLVED = "resolved", _("Resolved")
    CLOSED = "closed", _("Closed")
    CANCELLED = "cancelled", _("Cancelled")


class ReconcileDataQuerySourceChoices(models.TextChoices):
    MANUAL = "manual", _("Manual")
    SYSTEM = "system", _("System")
    IMPORT = "import", _("Import")


class ReconcileDataQueryTypeChoices(models.TextChoices):
    MANUAL = "manual", _("Manual")
    VALIDATION = "validation", _("Validation")
    SDV = "sdv", _("SDV")
    MEDICAL = "medical", _("Medical")
    ELIGIBILITY = "eligibility", _("Eligibility")
    SYSTEM = "system", _("System")


class ReconcileDataQuerySeverityChoices(models.TextChoices):
    MINOR = "minor", _("Minor")
    MAJOR = "major", _("Major")
    CRITICAL = "critical", _("Critical")


class ReconcileDataQuery(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    status = models.CharField(
        max_length=32,
        choices=ReconcileDataQueryStatusChoices.choices,
    )
    source = models.CharField(
        max_length=16,
        choices=ReconcileDataQuerySourceChoices.choices,
    )
    query_type = models.CharField(
        max_length=32,
        choices=ReconcileDataQueryTypeChoices.choices,
    )
    severity = models.CharField(
        max_length=16,
        choices=ReconcileDataQuerySeverityChoices.choices,
        default=ReconcileDataQuerySeverityChoices.MINOR,
    )
    is_blocking = models.BooleanField(default=True)

    question_text = models.TextField()
    resolution_note = models.CharField(max_length=1000, null=True, blank=True)

    opened_at = models.DateTimeField()
    answered_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    reason_code = models.CharField(max_length=64, null=True, blank=True)

    page_state = models.ForeignKey(
        "datacapture.DataCapturePageState",
        on_delete=models.DO_NOTHING,
        db_column="page_state_id",
        related_name="reconcile_data_queries",
    )
    page_entry = models.ForeignKey(
        "datacapture.DataCapturePageEntry",
        on_delete=models.DO_NOTHING,
        db_column="page_entry_id",
        related_name="reconcile_data_queries",
        null=True,
        blank=True,
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
    data_version = models.IntegerField(null=True, blank=True)
    field_path = models.CharField(max_length=512, null=True, blank=True)
    value_snapshot = models.TextField(null=True, blank=True)

    assigned_to_id = models.BigIntegerField(null=True, blank=True)
    opened_by_id = models.BigIntegerField(null=True, blank=True)
    answered_by_id = models.BigIntegerField(null=True, blank=True)
    resolved_by_id = models.BigIntegerField(null=True, blank=True)
    closed_by_id = models.BigIntegerField(null=True, blank=True)
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
    "ReconcileDataQuerySeverityChoices",
    "ReconcileDataQuerySourceChoices",
    "ReconcileDataQueryStatusChoices",
    "ReconcileDataQueryTypeChoices",
]
