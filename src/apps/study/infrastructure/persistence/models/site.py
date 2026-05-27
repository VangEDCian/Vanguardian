from django.db import models

from apps.identity.infrastructure.persistence.models import User
from apps.study.infrastructure.persistence.models import Study


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
        permissions = (
            ("view_site_list", "Can view site list"),
            ("view_site_detail", "Can view site detail"),
            ("create_site", "Can create site"),
            ("update_site", "Can update site"),
            ("delete_site", "Can delete site"),
        )
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
        managed = True
        default_permissions = ()
        ordering = ('site',)
        permissions = (
            ("view_site_membership_list", "Can view site membership list"),
            ("view_site_membership_detail", "Can view site membership detail"),
            ("create_site_membership", "Can create site membership"),
            ("update_site_membership", "Can update site membership"),
            ("delete_site_membership", "Can delete site membership"),

            # other
            ("view_site_membership_history", "Can view site membership audit history"),

            # # filter
            # ("filter_site_by_code", "Can filter studies by code"),
            # ("filter_site_by_study", "Can filter studies by study"),
            #
            # # field
            # ("view_site_field_code", "Can view field code"),
            # ("view_site_field_name", "Can view field name"),
            # ("view_site_field_investigator", "Can view field investigator"),
            # ("view_site_field_study", "Can view field study"),
        )
        indexes = [
            models.Index(
                fields=["study_id", "site_id", "user_id"],
                name="site_mship_study_site_user_idx",
            ),
            models.Index(
                fields=["user_id", "study_id", "site_id"],
                name="site_mship_usr_study_site_uq",
            ),
            models.Index(
                fields=["user_id", "site_id", "status"],
                name="site_mship_usr_scope_stat_idx",
            ),
        ]
        verbose_name = "site membership"
        verbose_name_plural = "sites membership"
