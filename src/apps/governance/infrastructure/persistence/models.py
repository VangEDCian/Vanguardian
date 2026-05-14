from django.db import models


class GovernanceDatabaseLock(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    status = models.CharField(max_length=16, default="locked")
    level = models.CharField(max_length=32, default="database")
    reason = models.TextField(null=True, blank=True)

    locked_at = models.DateTimeField()
    unlocked_at = models.DateTimeField(null=True, blank=True)
    locked_by_id = models.BigIntegerField(null=True, blank=True)
    unlocked_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "governance_databaselock"
        managed = False
        default_permissions = ()
        verbose_name = "governance database lock"
        verbose_name_plural = "governance database locks"


class GovernanceLockRecord(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    status = models.CharField(max_length=16, default="locked")
    level = models.CharField(max_length=32, default="page")
    reason = models.TextField(null=True, blank=True)

    subject_id = models.BigIntegerField(null=True, blank=True)
    visit_id = models.BigIntegerField(null=True, blank=True)
    crf_template_id = models.BigIntegerField(null=True, blank=True)
    page_state_id = models.BigIntegerField(null=True, blank=True)

    locked_at = models.DateTimeField()
    unlocked_at = models.DateTimeField(null=True, blank=True)
    locked_by_id = models.BigIntegerField(null=True, blank=True)
    unlocked_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "governance_lockrecord"
        managed = False
        default_permissions = ()
        verbose_name = "governance lock record"
        verbose_name_plural = "governance lock records"


__all__ = [
    "GovernanceDatabaseLock",
    "GovernanceLockRecord",
]
