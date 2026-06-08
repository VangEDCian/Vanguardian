from dataclasses import dataclass

from django.contrib.auth.models import Permission
from django.db.models import Q
from django.utils import timezone

from apps.identity.models import (
    MembershipStatus,
    RoleAssignmentStatus,
    RoleScopeLevel,
    StudyMembership,
    StudyMembershipRole,
    StudySiteMembership,
    StudySiteMembershipRole,
    UserRole,
)
from apps.study.public import study_site_belongs_to_study


@dataclass(frozen=True)
class PermissionLookup:
    id: int
    code: str


@dataclass(frozen=True)
class RoleMatch:
    scope: str
    role_id: int


class ContextualAuthorizationRepository:
    def resolve_permission(self, permission: str) -> PermissionLookup | None:
        permission = str(permission or "").strip()
        if not permission:
            return None

        found_permission = Permission.objects.select_related("content_type").filter(codename=permission).first()
        if found_permission is None and "." in permission:
            app_label, codename = permission.split(".", 1)
            found_permission = (
                Permission.objects.select_related("content_type")
                .filter(content_type__app_label=app_label, codename=codename)
                .first()
            )
        if found_permission is None:
            return None
        return PermissionLookup(id=found_permission.pk, code=self.permission_code_for(found_permission))

    def study_site_belongs_to_study(self, *, study_id: int, study_site_id: int) -> bool:
        return study_site_belongs_to_study(study_id=study_id, study_site_id=study_site_id)

    def find_study_role_match(self, *, user_id: int, study_id: int, permission_id: int) -> RoleMatch | None:
        assignment = (
            StudyMembershipRole.objects.select_related("role")
            .filter(
                self._current_membership_window_q("study_membership"),
                study_membership__user_id=user_id,
                study_membership__study_id=study_id,
                study_membership__deleted=False,
                study_membership__status=MembershipStatus.ACTIVE,
                status=RoleAssignmentStatus.ACTIVE,
                revoked_at__isnull=True,
                role__scope_level=RoleScopeLevel.STUDY,
                role__study_id=study_id,
                role__is_active=True,
            )
            .filter(self._role_permission_q(permission_id))
            .order_by("role_id", "id")
            .first()
        )
        if assignment is None:
            return None
        return RoleMatch(scope=RoleScopeLevel.STUDY, role_id=assignment.role_id)

    def has_active_study_membership(self, *, user_id: int, study_id: int) -> bool:
        return StudyMembership.objects.filter(
            self._current_window_q(),
            user_id=user_id,
            study_id=study_id,
            deleted=False,
            status=MembershipStatus.ACTIVE,
        ).exists()

    def has_active_study_role_assignment(self, *, user_id: int, study_id: int) -> bool:
        return StudyMembershipRole.objects.filter(
            self._current_membership_window_q("study_membership"),
            study_membership__user_id=user_id,
            study_membership__study_id=study_id,
            study_membership__deleted=False,
            study_membership__status=MembershipStatus.ACTIVE,
            status=RoleAssignmentStatus.ACTIVE,
            revoked_at__isnull=True,
            role__scope_level=RoleScopeLevel.STUDY,
            role__study_id=study_id,
            role__is_active=True,
        ).exists()

    def find_study_site_role_match(
        self,
        *,
        user_id: int,
        study_id: int,
        study_site_id: int,
        permission_id: int,
    ) -> RoleMatch | None:
        assignment = (
            StudySiteMembershipRole.objects.select_related("role")
            .filter(
                self._current_membership_window_q("study_site_membership"),
                study_site_membership__user_id=user_id,
                study_site_membership__study_id=study_id,
                study_site_membership__site_id=study_site_id,
                study_site_membership__deleted=False,
                study_site_membership__status=MembershipStatus.ACTIVE,
                status=RoleAssignmentStatus.ACTIVE,
                revoked_at__isnull=True,
                role__scope_level=RoleScopeLevel.STUDY_SITE,
                role__study_id=study_id,
                role__is_active=True,
            )
            .filter(self._role_permission_q(permission_id))
            .order_by("role_id", "id")
            .first()
        )
        if assignment is None:
            return None
        return RoleMatch(scope=RoleScopeLevel.STUDY_SITE, role_id=assignment.role_id)

    def has_active_study_site_membership(self, *, user_id: int, study_id: int, study_site_id: int) -> bool:
        return StudySiteMembership.objects.filter(
            self._current_window_q(),
            user_id=user_id,
            study_id=study_id,
            site_id=study_site_id,
            deleted=False,
            status=MembershipStatus.ACTIVE,
        ).exists()

    def has_active_study_site_role_assignment(self, *, user_id: int, study_id: int, study_site_id: int) -> bool:
        return StudySiteMembershipRole.objects.filter(
            self._current_membership_window_q("study_site_membership"),
            study_site_membership__user_id=user_id,
            study_site_membership__study_id=study_id,
            study_site_membership__site_id=study_site_id,
            study_site_membership__deleted=False,
            study_site_membership__status=MembershipStatus.ACTIVE,
            status=RoleAssignmentStatus.ACTIVE,
            revoked_at__isnull=True,
            role__scope_level=RoleScopeLevel.STUDY_SITE,
            role__study_id=study_id,
            role__is_active=True,
        ).exists()

    def find_global_role_match(self, *, user_id: int, permission_id: int) -> RoleMatch | None:
        assignment = (
            UserRole.objects.select_related("role")
            .filter(
                user_id=user_id,
                role__scope_level=RoleScopeLevel.GLOBAL,
                role__is_active=True,
            )
            .filter(self._role_permission_q(permission_id))
            .order_by("role_id", "id")
            .first()
        )
        if assignment is None:
            return None
        return RoleMatch(scope=RoleScopeLevel.GLOBAL, role_id=assignment.role_id)

    @staticmethod
    def permission_code_for(permission: Permission) -> str:
        return f"{permission.content_type.app_label}.{permission.codename}"

    @staticmethod
    def _role_permission_q(permission_id: int):
        return Q(role__permissions__id=permission_id) | Q(role__groups__permissions__id=permission_id)

    @staticmethod
    def _current_membership_window_q(prefix: str):
        now = timezone.now()
        return (Q(**{f"{prefix}__valid_from__isnull": True}) | Q(**{f"{prefix}__valid_from__lte": now})) & (
            Q(**{f"{prefix}__valid_to__isnull": True}) | Q(**{f"{prefix}__valid_to__gt": now})
        )

    @staticmethod
    def _current_window_q():
        now = timezone.now()
        return (Q(valid_from__isnull=True) | Q(valid_from__lte=now)) & (
            Q(valid_to__isnull=True) | Q(valid_to__gt=now)
        )
