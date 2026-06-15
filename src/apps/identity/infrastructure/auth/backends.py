from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class IdentifierBackend(ModelBackend):
    """
    Allow login with username, email, or phone number while keeping Django's
    default password and active-user checks.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        user_model = get_user_model()
        if username is None:
            username = kwargs.get(user_model.USERNAME_FIELD)

        if username is None or password is None:
            return None

        identifier = username.strip()
        if not identifier:
            return None

        user = self._get_user_by_identifier(identifier)
        if user is None:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def _get_user_by_identifier(self, identifier):
        user_model = get_user_model()
        manager = user_model._default_manager
        lookups = (
            {user_model.USERNAME_FIELD: identifier},
            {"email__iexact": identifier},
            {"phone_number": identifier},
        )

        for lookup in lookups:
            try:
                return manager.get(**lookup)
            except user_model.DoesNotExist:
                continue
            except user_model.MultipleObjectsReturned:
                return None

        return None

    def has_perm(self, user_obj, perm, obj=None):
        if not self.user_can_authenticate(user_obj):
            return False
        if getattr(user_obj, "is_superuser", False):
            return True
        permission = self._get_identity_permission(perm)
        if permission is None:
            return False
        return self._user_has_role_permission(user_obj, permission.pk)

    def get_all_permissions(self, user_obj, obj=None):
        if not self.user_can_authenticate(user_obj):
            return set()
        if getattr(user_obj, "is_superuser", False):
            return self._all_identity_permission_codes()

        from apps.identity.models import (
            RoleAssignmentStatus,
            StudyMembershipRole,
            StudySiteMembershipRole,
            UserRole,
        )

        permissions = set()
        role_querysets = (
            UserRole.objects.filter(user_id=user_obj.pk, role__is_active=True),
            StudyMembershipRole.objects.filter(
                study_membership__user_id=user_obj.pk,
                status=RoleAssignmentStatus.ACTIVE,
                role__is_active=True,
            ),
            StudySiteMembershipRole.objects.filter(
                study_site_membership__user_id=user_obj.pk,
                status=RoleAssignmentStatus.ACTIVE,
                role__is_active=True,
            ),
        )
        for queryset in role_querysets:
            for permission in queryset.values_list(
                "role__permissions__app_label",
                "role__permissions__codename",
            ):
                app_label, codename = permission
                if app_label and codename:
                    permissions.add(self._permission_code(app_label, codename))
        return permissions

    def has_module_perms(self, user_obj, app_label):
        return any(
            permission_code.startswith(f"{app_label}.")
            for permission_code in self.get_all_permissions(user_obj)
        )

    @staticmethod
    def _get_identity_permission(permission_code):
        from apps.identity.models import IdentityPermission

        normalized_code = str(permission_code or "").strip()
        if not normalized_code:
            return None
        permission = IdentityPermission.objects.filter(codename=normalized_code).first()
        if permission is not None:
            return permission
        if "." not in normalized_code:
            return None
        app_label, codename = normalized_code.split(".", 1)
        return IdentityPermission.objects.filter(app_label=app_label, codename=codename).first()

    @staticmethod
    def _user_has_role_permission(user_obj, permission_id):
        from apps.identity.models import (
            RoleAssignmentStatus,
            StudyMembershipRole,
            StudySiteMembershipRole,
            UserRole,
        )

        return (
            UserRole.objects.filter(
                user_id=user_obj.pk,
                role__is_active=True,
                role__permissions__id=permission_id,
            ).exists()
            or StudyMembershipRole.objects.filter(
                IdentifierBackend._active_study_membership_q(),
                study_membership__user_id=user_obj.pk,
                status=RoleAssignmentStatus.ACTIVE,
                role__is_active=True,
                role__permissions__id=permission_id,
            ).exists()
            or StudySiteMembershipRole.objects.filter(
                IdentifierBackend._active_site_membership_q(),
                study_site_membership__user_id=user_obj.pk,
                status=RoleAssignmentStatus.ACTIVE,
                role__is_active=True,
                role__permissions__id=permission_id,
            ).exists()
        )

    @staticmethod
    def _active_study_membership_q():
        return Q(study_membership__deleted=False, study_membership__status="ACTIVE")

    @staticmethod
    def _active_site_membership_q():
        return Q(study_site_membership__deleted=False, study_site_membership__status="ACTIVE")

    @staticmethod
    def _all_identity_permission_codes():
        from apps.identity.models import IdentityPermission

        return {
            IdentifierBackend._permission_code(permission.app_label, permission.codename)
            for permission in IdentityPermission.objects.all()
        }

    @staticmethod
    def _permission_code(app_label, codename):
        if "." in codename and codename == codename.upper():
            return codename
        return f"{app_label}.{codename}"
