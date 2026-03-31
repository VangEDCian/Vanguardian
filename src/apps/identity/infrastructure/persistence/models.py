from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models


class User(AbstractUser):
    """
    Identity user stays compatible with django-auth's runtime semantics while
    reserving ownership of the concrete user table for the DB-first schema.
    """

    email = models.EmailField(blank=True, null=True, unique=True)
    display_name = models.CharField(max_length=255, blank=True, default="")
    phone_number = models.CharField(max_length=32, blank=True, null=True, unique=True)

    def save(self, *args, **kwargs):
        self.email = self._normalize_optional_identifier(self.email)
        self.phone_number = self._normalize_optional_identifier(self.phone_number)
        super().save(*args, **kwargs)

    @staticmethod
    def _normalize_optional_identifier(value):
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None

    class Meta(AbstractUser.Meta):
        db_table = "identity_user"
        managed = False
        default_permissions = ()
        verbose_name = "user"
        verbose_name_plural = "users"


class Role(models.Model):
    """
    Role is a project-defined access bundle that can combine both direct
    django permissions and permission groups.
    """

    name = models.CharField(max_length=150, unique=True)
    description = models.CharField(max_length=255, blank=True, default="")
    groups = models.ManyToManyField(
        Group,
        through="RoleGroup",
        related_name="identity_roles",
        blank=True,
    )
    permissions = models.ManyToManyField(
        Permission,
        through="RolePermission",
        related_name="identity_roles",
        blank=True,
    )

    class Meta:
        db_table = "identity_role"
        managed = False
        default_permissions = ()
        verbose_name = "role"
        verbose_name_plural = "roles"


class RoleGroup(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)

    class Meta:
        db_table = "identity_role_groups"
        managed = False
        unique_together = (("role", "group"),)
        default_permissions = ()
        permissions = ()
        verbose_name = "role group mapping"
        verbose_name_plural = "role group mappings"


class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        db_table = "identity_role_permissions"
        managed = False
        unique_together = (("role", "permission"),)
        default_permissions = ()
        permissions = ()
        verbose_name = "role permission mapping"
        verbose_name_plural = "role permission mappings"


class StudyMembership(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    study_id = models.BigIntegerField()
    deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "study_membership"
        managed = False
        unique_together = (("user", "study_id"),)
        default_permissions = ()
        permissions = ()
        verbose_name = "study membership"
        verbose_name_plural = "study memberships"


class StudySiteMembership(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    study_id = models.BigIntegerField()
    site_id = models.BigIntegerField()
    deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "study_site_membership"
        managed = False
        unique_together = (("user", "study_id", "site_id"),)
        default_permissions = ()
        permissions = ()
        verbose_name = "study site membership"
        verbose_name_plural = "study site memberships"
