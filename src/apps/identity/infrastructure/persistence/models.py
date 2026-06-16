from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class RoleScopeLevel(models.TextChoices):
    GLOBAL = "GLOBAL", "Global"
    STUDY = "STUDY", "Study"
    STUDY_SITE = "STUDY_SITE", "Study site"


class MembershipStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"
    REVOKED = "REVOKED", "Revoked"
    EXPIRED = "EXPIRED", "Expired"


class RoleAssignmentStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    REVOKED = "REVOKED", "Revoked"
    EXPIRED = "EXPIRED", "Expired"


class User(AbstractUser):
    groups = None
    user_permissions = None

    is_staff = models.BooleanField(default=True)
    email = models.EmailField(blank=True, null=True, unique=True)
    deleted = models.BooleanField(default=False)
    display_name = models.CharField(max_length=255, blank=True, default="")
    phone_number = models.CharField(max_length=32, blank=True, null=True, unique=True)
    attempt_login  = models.SmallIntegerField(default=0)
    active_session_key = models.CharField(max_length=40, blank=True, default="")
    active_session_started_at = models.DateTimeField(blank=True, null=True)

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
        managed = True
        default_permissions = ()
        indexes = [
            models.Index(fields=["username"], name="identity_user_username_idx"),
            models.Index(fields=["email"], name="identity_user_email_idx"),
            models.Index(fields=["phone_number"], name="identity_user_phone_idx"),
            models.Index(fields=["active_session_key"], name="identity_user_session_idx"),
        ]
        verbose_name = "user"
        verbose_name_plural = "users"


class IdentityPermission(models.Model):
    app_label = models.CharField(max_length=64)
    codename = models.CharField(max_length=100)
    name = models.CharField(max_length=255)

    @property
    def permission_code(self):
        if "." in self.codename and self.codename == self.codename.upper():
            return self.codename
        return f"{self.app_label}.{self.codename}"

    class Meta:
        db_table = "identity_permission"
        managed = True
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["app_label", "codename"],
                name="identity_permission_app_code_uq",
            ),
        ]
        indexes = [
            models.Index(fields=["app_label", "codename"], name="identity_perm_app_code_idx"),
            models.Index(fields=["codename"], name="identity_perm_code_idx"),
        ]
        verbose_name = "identity permission"
        verbose_name_plural = "identity permissions"


class Role(models.Model):
    """Role is a project-defined access bundle of identity permissions."""

    study_id = models.BigIntegerField()
    code = models.CharField(max_length=100, blank=True, default="")
    name = models.CharField(max_length=150)
    description = models.CharField(max_length=255, blank=True, default="")
    scope_level = models.CharField(
        max_length=30,
        choices=RoleScopeLevel.choices,
        default=RoleScopeLevel.STUDY_SITE,
    )
    is_system_role = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    version_no = models.PositiveIntegerField(default=1)
    permissions = models.ManyToManyField(
        IdentityPermission,
        through="RolePermission",
        related_name="identity_roles",
        blank=True,
    )

    class Meta:
        db_table = "identity_role"
        managed = True
        default_permissions = ()
        unique_together = (("study_id", "name"),)
        indexes = [
            models.Index(fields=["study_id", "name"], name="identity_role_study_name_idx"),
            models.Index(fields=["name"], name="identity_role_name_idx"),
            models.Index(fields=["code", "scope_level", "version_no"], name="identity_role_scope_ver_idx"),
            models.Index(fields=["study_id", "scope_level", "is_active"], name="identity_role_scope_active_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["study_id", "code", "scope_level", "version_no"],
                name="identity_role_study_code_scope_ver_uniq",
            ),
        ]
        verbose_name = "role"
        verbose_name_plural = "roles"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.name.upper().replace(" ", "_")
        super().save(*args, **kwargs)


class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(IdentityPermission, on_delete=models.CASCADE)

    class Meta:
        db_table = "identity_role_permissions"
        managed = True
        unique_together = (("role", "permission"),)
        default_permissions = ()
        indexes = [
            models.Index(fields=["role", "permission"], name="identity_rp_role_perm_idx"),
        ]
        verbose_name = "role permission mapping"
        verbose_name_plural = "role permission mappings"


class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="identity_user_roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="identity_user_roles")

    class Meta:
        db_table = "identity_user_roles"
        managed = True
        unique_together = (("user", "role"),)
        default_permissions = ()
        verbose_name = "user role mapping"
        verbose_name_plural = "user role mappings"


class StudyMembership(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="study_memberships")
    study_id = models.BigIntegerField()
    role = models.CharField(max_length=64)
    is_global_role = models.BooleanField(default=False)
    status = models.CharField(
        max_length=30,
        choices=MembershipStatus.choices,
        default=MembershipStatus.ACTIVE,
    )
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)

    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "study_membership"
        managed = True
        unique_together = (("user", "study_id"),)
        default_permissions = ()
        indexes = [
            models.Index(fields=["user", "study_id"], name="study_mship_user_study_idx"),
            models.Index(fields=["study_id", "user"], name="study_mship_study_user_idx"),
            models.Index(fields=["user", "study_id", "status"], name="study_mship_usr_scope_stat_idx"),
        ]
        verbose_name = "study membership"
        verbose_name_plural = "study memberships"


class StudySiteMembership(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="study_site_memberships")
    study_id = models.BigIntegerField()
    site_id = models.BigIntegerField()
    status = models.CharField(
        max_length=30,
        choices=MembershipStatus.choices,
        default=MembershipStatus.ACTIVE,
    )
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)

    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "study_site_membership"
        managed = True
        unique_together = (("user", "study_id", "site_id"),)
        default_permissions = ()
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
        verbose_name = "study site membership"
        verbose_name_plural = "study site memberships"


class StudyMembershipRole(models.Model):
    study_membership = models.ForeignKey(
        StudyMembership,
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="study_membership_assignments")
    assigned_at = models.DateTimeField()
    assigned_by_id = models.BigIntegerField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by_id = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=30,
        choices=RoleAssignmentStatus.choices,
        default=RoleAssignmentStatus.ACTIVE,
    )

    class Meta:
        db_table = "study_membership_role"
        managed = True
        unique_together = (("study_membership", "role"),)
        default_permissions = ()
        indexes = [
            models.Index(fields=["study_membership", "status"], name="study_mship_role_status_idx"),
            models.Index(fields=["role", "status"], name="study_mship_role_stat_idx"),
        ]
        verbose_name = "study membership role assignment"
        verbose_name_plural = "study membership role assignments"

    def clean(self):
        if self.role_id and self.role.scope_level != RoleScopeLevel.STUDY:
            raise ValidationError("Study membership can only be assigned STUDY roles.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class StudySiteMembershipRole(models.Model):
    study_site_membership = models.ForeignKey(
        StudySiteMembership,
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="study_site_membership_assignments")
    assigned_at = models.DateTimeField()
    assigned_by_id = models.BigIntegerField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by_id = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=30,
        choices=RoleAssignmentStatus.choices,
        default=RoleAssignmentStatus.ACTIVE,
    )

    class Meta:
        db_table = "study_site_membership_role"
        managed = True
        unique_together = (("study_site_membership", "role"),)
        default_permissions = ()
        indexes = [
            models.Index(fields=["study_site_membership", "status"], name="site_mship_role_status_idx"),
            models.Index(fields=["role", "status"], name="site_mship_role_stat_idx"),
        ]
        verbose_name = "study site membership role assignment"
        verbose_name_plural = "study site membership role assignments"

    def clean(self):
        if self.role_id and self.role.scope_level != RoleScopeLevel.STUDY_SITE:
            raise ValidationError("Study-site membership can only be assigned STUDY_SITE roles.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class DelegationTask(models.Model):
    code = models.CharField(max_length=64, primary_key=True)
    name = models.CharField(max_length=255)
    required_permission_code = models.CharField(max_length=100, blank=True, default="")
    requires_training = models.BooleanField(default=False)
    requires_pi_approval = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "identity_delegation_task"
        managed = True
        default_permissions = ()
        verbose_name = "delegation task"
        verbose_name_plural = "delegation tasks"


class DelegationOfAuthority(models.Model):
    study_site_id = models.BigIntegerField()
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="delegations")
    task_code = models.CharField(max_length=64)
    delegated_by_user_id = models.BigIntegerField()
    status = models.CharField(max_length=30, default="PENDING")
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField()
    created_by_id = models.BigIntegerField(null=True, blank=True)
    signature_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "identity_delegation_of_authority"
        managed = True
        default_permissions = ()
        indexes = [
            models.Index(fields=["user", "study_site_id", "task_code", "status"], name="ident_doa_usr_scope_task_idx"),
        ]
        verbose_name = "delegation of authority"
        verbose_name_plural = "delegations of authority"


class TrainingRequirement(models.Model):
    study_id = models.BigIntegerField()
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)
    task_code = models.CharField(max_length=64, blank=True, default="")
    permission_code = models.CharField(max_length=100, blank=True, default="")
    training_code = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "identity_training_requirement"
        managed = True
        default_permissions = ()
        indexes = [
            models.Index(fields=["study_id", "permission_code", "is_active"], name="identity_train_req_perm_idx"),
            models.Index(fields=["study_id", "task_code", "is_active"], name="identity_train_req_task_idx"),
        ]
        verbose_name = "training requirement"
        verbose_name_plural = "training requirements"


class TrainingCompletion(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name="training_completions")
    study_id = models.BigIntegerField()
    training_code = models.CharField(max_length=100)
    completed_at = models.DateTimeField()
    expires_at = models.DateTimeField(null=True, blank=True)
    evidence_file_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "identity_training_completion"
        managed = True
        default_permissions = ()
        indexes = [
            models.Index(fields=["user", "study_id", "training_code"], name="identity_train_done_user_idx"),
        ]
        verbose_name = "training completion"
        verbose_name_plural = "training completions"
