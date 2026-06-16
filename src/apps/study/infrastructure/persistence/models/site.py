from django.db import models

from apps.identity.infrastructure.persistence.models import User

from .study import Study


class Site(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)
    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    code = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    investigator = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        db_column="investigator",
        null=True,
        blank=True,
        related_name="study_sites_as_investigator",
    )
    study = models.ForeignKey(Study, on_delete=models.CASCADE, db_column='study_id')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "study_site"
        managed = True
        ordering = ('id',)
        default_permissions = ()
        indexes = [
            models.Index(fields=["study", "code"], name="uq_study_site_study_code"),
            models.Index(fields=["deleted"], name="study_study_deleted_idx"),
            models.Index(fields=["created_by_id"], name="study_study_created_by_id_idx"),
            models.Index(
                fields=["study_id", "deleted", "created_by_id"],
                name="site_study_del_creator_idx",
            ),
        ]
        verbose_name = "site"
        verbose_name_plural = "sites"


class SiteMembership(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)
    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id')
    study = models.ForeignKey(Study, on_delete=models.CASCADE, db_column='study_id')
    site = models.ForeignKey(Site, on_delete=models.CASCADE, db_column='site_id')
    status = models.CharField(max_length=30, default="ACTIVE")
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "study_site_membership"
        managed = False
        default_permissions = ()
        ordering = ('site',)
        verbose_name = "site membership"
        verbose_name_plural = "sites membership"
