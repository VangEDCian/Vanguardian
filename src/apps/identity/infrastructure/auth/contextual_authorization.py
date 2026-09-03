from dataclasses import dataclass

from django.db.models import Q
from django.utils import timezone

from apps.identity.models import (
    IdentityPermission,
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
    def __init__(self, *, use_request_cache: bool = False):
        self.use_request_cache = use_request_cache
        self._permission_lookups = None
        self._study_site_context_cache = {}
        self._study_role_match_cache = {}
        self._site_role_match_cache = {}
        self._active_study_membership_cache = {}
        self._active_study_role_cache = {}
        self._active_site_membership_cache = {}
        self._active_site_role_cache = {}

    def resolve_permission(self, permission: str) -> PermissionLookup | None:
        permission = str(permission or "").strip()
        if not permission:
            return None

        if self.use_request_cache:
            by_codename, by_app_codename = self._get_permission_lookups()
            found_permission = by_codename.get(permission)
            if found_permission is None and "." in permission:
                app_label, codename = permission.split(".", 1)
                found_permission = by_app_codename.get((app_label, codename))
            return found_permission

        found_permission = IdentityPermission.objects.filter(codename=permission).first()
        if found_permission is None and "." in permission:
            app_label, codename = permission.split(".", 1)
            found_permission = (
                IdentityPermission.objects
                .filter(app_label=app_label, codename=codename)
                .first()
            )
        if found_permission is None:
            return None
        return PermissionLookup(id=found_permission.pk, code=self.permission_code_for(found_permission))

    def study_site_belongs_to_study(self, *, study_id: int, study_site_id: int) -> bool:
        cache_key = (study_id, study_site_id)
        if self.use_request_cache and cache_key in self._study_site_context_cache:
            return self._study_site_context_cache[cache_key]

        result = study_site_belongs_to_study(study_id=study_id, study_site_id=study_site_id)
        if self.use_request_cache:
            self._study_site_context_cache[cache_key] = result
        return result

    def find_study_role_match(self, *, user_id: int, study_id: int, permission_id: int) -> RoleMatch | None:
        if self.use_request_cache:
            cache_key = (user_id, study_id)
            if cache_key not in self._study_role_match_cache:
                assignments = (
                    StudyMembershipRole.objects.select_related("role")
                    .prefetch_related("role__permissions")
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
                    .order_by("role_id", "id")
                )
                self._study_role_match_cache[cache_key] = self._permission_role_matches(
                    assignments,
                    scope=RoleScopeLevel.STUDY,
                )
            return self._study_role_match_cache[cache_key].get(permission_id)

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
        cache_key = (user_id, study_id)
        if self.use_request_cache and cache_key in self._active_study_membership_cache:
            return self._active_study_membership_cache[cache_key]

        result = StudyMembership.objects.filter(
            self._current_window_q(),
            user_id=user_id,
            study_id=study_id,
            deleted=False,
            status=MembershipStatus.ACTIVE,
        ).exists()
        if self.use_request_cache:
            self._active_study_membership_cache[cache_key] = result
        return result

    def has_active_study_role_assignment(self, *, user_id: int, study_id: int) -> bool:
        cache_key = (user_id, study_id)
        if self.use_request_cache and cache_key in self._active_study_role_cache:
            return self._active_study_role_cache[cache_key]

        result = StudyMembershipRole.objects.filter(
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
        if self.use_request_cache:
            self._active_study_role_cache[cache_key] = result
        return result

    def find_study_site_role_match(
        self,
        *,
        user_id: int,
        study_id: int,
        study_site_id: int,
        permission_id: int,
    ) -> RoleMatch | None:
        if self.use_request_cache:
            cache_key = (user_id, study_id, study_site_id)
            if cache_key not in self._site_role_match_cache:
                assignments = (
                    StudySiteMembershipRole.objects.select_related("role")
                    .prefetch_related("role__permissions")
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
                    .order_by("role_id", "id")
                )
                self._site_role_match_cache[cache_key] = self._permission_role_matches(
                    assignments,
                    scope=RoleScopeLevel.STUDY_SITE,
                )
            return self._site_role_match_cache[cache_key].get(permission_id)

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
        cache_key = (user_id, study_id, study_site_id)
        if self.use_request_cache and cache_key in self._active_site_membership_cache:
            return self._active_site_membership_cache[cache_key]

        result = StudySiteMembership.objects.filter(
            self._current_window_q(),
            user_id=user_id,
            study_id=study_id,
            site_id=study_site_id,
            deleted=False,
            status=MembershipStatus.ACTIVE,
        ).exists()
        if self.use_request_cache:
            self._active_site_membership_cache[cache_key] = result
        return result

    def has_active_study_site_role_assignment(self, *, user_id: int, study_id: int, study_site_id: int) -> bool:
        cache_key = (user_id, study_id, study_site_id)
        if self.use_request_cache and cache_key in self._active_site_role_cache:
            return self._active_site_role_cache[cache_key]

        result = StudySiteMembershipRole.objects.filter(
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
        if self.use_request_cache:
            self._active_site_role_cache[cache_key] = result
        return result

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
    def permission_code_for(permission: IdentityPermission) -> str:
        return permission.permission_code

    def _get_permission_lookups(self):
        if self._permission_lookups is None:
            by_codename = {}
            by_app_codename = {}
            for permission in IdentityPermission.objects.order_by("id"):
                lookup = PermissionLookup(
                    id=permission.pk,
                    code=self.permission_code_for(permission),
                )
                by_codename.setdefault(permission.codename, lookup)
                by_app_codename[(permission.app_label, permission.codename)] = lookup
            self._permission_lookups = (by_codename, by_app_codename)
        return self._permission_lookups

    @staticmethod
    def _permission_role_matches(assignments, *, scope: str) -> dict[int, RoleMatch]:
        matches = {}
        for assignment in assignments:
            role_match = RoleMatch(scope=scope, role_id=assignment.role_id)
            for permission in assignment.role.permissions.all():
                matches.setdefault(permission.pk, role_match)
        return matches

    @staticmethod
    def _role_permission_q(permission_id: int):
        return Q(role__permissions__id=permission_id)

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
