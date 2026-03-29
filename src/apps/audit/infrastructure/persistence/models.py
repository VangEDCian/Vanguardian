from django.db import models


class AuditEvent(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    action = models.CharField(max_length=64)
    object_type = models.CharField(max_length=64)
    object_id = models.CharField(max_length=64)
    before_data = models.TextField(default="{}")
    after_data = models.TextField(default="{}")
    ip_address = models.CharField(max_length=39, blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True, default="")

    user = models.ForeignKey(
        "identity.User",
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="audit_events",
    )
    created_by = models.ForeignKey(
        "identity.User",
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="created_audit_events",
    )
    updated_by = models.ForeignKey(
        "identity.User",
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="updated_audit_events",
    )

    class Meta:
        db_table = "audit_auditevent"
        managed = False
        default_permissions = ()
        permissions = ()
        indexes = [
            models.Index(
                fields=("object_type", "object_id", "created_at"),
                name="audit_auditevent_object_timeline_idx",
            ),
        ]
        verbose_name = "audit event"
        verbose_name_plural = "audit events"
