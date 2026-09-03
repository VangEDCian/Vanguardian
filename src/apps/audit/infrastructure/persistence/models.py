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
        managed = True
        default_permissions = ()
        indexes = [
            models.Index(
                fields=("object_type", "object_id", "created_at"),
                name="audit_auditevent_obj_time_idx",
            ),
        ]
        verbose_name = "audit event"
        verbose_name_plural = "audit events"


class ElectronicSignature(models.Model):
    created_at = models.DateTimeField()

    signed_by = models.ForeignKey(
        "identity.User",
        on_delete=models.DO_NOTHING,
        db_column="signed_by_id",
        related_name="electronic_signatures",
    )
    signed_at = models.DateTimeField()
    reauthenticated_at = models.DateTimeField(null=True, blank=True)

    signer_name_snapshot = models.CharField(max_length=255)

    signature_meaning_code = models.CharField(max_length=64)
    signature_meaning_text = models.TextField()

    authentication_method = models.CharField(max_length=32)
    authentication_context_id = models.CharField(max_length=128, null=True, blank=True)

    signed_object_type = models.CharField(max_length=64)
    signed_object_id = models.CharField(max_length=64)
    signed_payload_hash = models.CharField(max_length=64)

    ip_address = models.CharField(max_length=39, null=True, blank=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "audit_electronicsignature"
        managed = True
        default_permissions = ()
        indexes = [
            models.Index(fields=("signed_by", "signed_at"), name="audit_esig_user_time_idx"),
            models.Index(
                fields=("signed_object_type", "signed_object_id"),
                name="audit_esig_object_idx",
            ),
            models.Index(fields=("signed_payload_hash",), name="audit_esig_payload_hash_idx"),
        ]
        verbose_name = "electronic signature"
        verbose_name_plural = "electronic signatures"
