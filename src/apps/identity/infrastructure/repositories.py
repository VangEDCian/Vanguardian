from django.db.models import Q
from django.utils import timezone

from apps.audit.infrastructure.persistence.models import AuditEvent
from apps.identity.infrastructure.sonic import SonicSearchAdapter
from apps.identity.models import (
    Role,
    RoleAssignmentStatus,
    RoleScopeLevel,
    StudyMembership,
    StudyMembershipRole,
    StudySiteMembership,
    StudySiteMembershipRole,
    User,
    UserRole,
)
from apps.shared.constants import AuditEventAction, AuditEventObjectType
from apps.study.models import Site, Study


class DjangoIdentityUserRepository:
    def __init__(self, *, sonic_search_adapter=None):
        self.sonic_search_adapter = sonic_search_adapter or SonicSearchAdapter()

    def build_user(self, **values):
        return User(**values)

    def save_user(self, user):
        user.save()
        return user

    def get_user(self, *, user_id):
        return User.objects.filter(pk=user_id).first()

    def list_users(self, *, order_by=()):
        return User.objects.filter(deleted=False).order_by(*order_by)

    def list_users_accessible_to_user(self, user, *, order_by=()):
        queryset = self.list_users(order_by=order_by)
        if user is None or user.is_superuser or user.has_perm("identity.view_user_list"):
            return queryset

        allowed_study_ids = self.list_study_memberships_for_user(user).values("study_id")
        allowed_site_ids = self.list_site_memberships_for_user(user).values("site_id")
        return queryset.filter(
            Q(study_memberships__study_id__in=allowed_study_ids)
            | Q(study_site_memberships__site_id__in=allowed_site_ids)
        ).distinct()

    def user_is_accessible_to_user(self, *, actor_user, target_user):
        if actor_user is None or target_user is None:
            return False
        if actor_user.is_superuser or actor_user.has_perm("identity.view_user_detail"):
            return True

        return self.list_users_accessible_to_user(actor_user).filter(pk=target_user.pk).exists()

    def get_user_for_detail(self, *, user_id, include_deleted=False):
        queryset = User.objects.filter(pk=user_id)
        if not include_deleted:
            queryset = queryset.filter(deleted=False)
        return queryset.first()

    def reload_user(self, user):
        return User.objects.get(pk=user.pk)

    def username_exists(self, *, username, exclude_user_id=None, deleted=None):
        queryset = User.objects.filter(username__iexact=username)
        queryset = self._apply_user_filters(queryset, exclude_user_id=exclude_user_id, deleted=deleted)
        return queryset.exists()

    def email_exists(self, *, email, exclude_user_id=None, deleted=None):
        queryset = User.objects.filter(email__iexact=email)
        queryset = self._apply_user_filters(queryset, exclude_user_id=exclude_user_id, deleted=deleted)
        return queryset.exists()

    def phone_number_exists(self, *, phone_number, exclude_user_id=None, deleted=None):
        queryset = User.objects.filter(phone_number=phone_number)
        queryset = self._apply_user_filters(queryset, exclude_user_id=exclude_user_id, deleted=deleted)
        return queryset.exists()

    def list_roles(self, *, study_ids=(), scope_levels=()):
        queryset = Role.objects.all()
        normalized_study_ids = self._normalize_ids(study_ids)
        if normalized_study_ids:
            queryset = queryset.filter(study_id__in=normalized_study_ids)
        normalized_scope_levels = tuple(str(scope_level or "").strip() for scope_level in scope_levels if str(scope_level or "").strip())
        if normalized_scope_levels:
            queryset = queryset.filter(scope_level__in=normalized_scope_levels)
        return queryset.order_by("study_id", "name")

    def list_user_roles(self, user):
        if user is None or not getattr(user, "pk", None):
            return UserRole.objects.none()
        return UserRole.objects.select_related("role").filter(user_id=user.pk).order_by("role__name")

    def set_user_roles(self, *, user, role_ids):
        if user is None or not getattr(user, "pk", None):
            return

        normalized_role_ids = []
        seen_role_ids = set()
        for role_id in role_ids or ():
            normalized_role_id = str(role_id).strip()
            if not normalized_role_id or normalized_role_id in seen_role_ids:
                continue
            if not normalized_role_id.isdigit():
                continue
            seen_role_ids.add(normalized_role_id)
            normalized_role_ids.append(int(normalized_role_id))

        UserRole.objects.filter(user_id=user.pk).delete()
        if not normalized_role_ids:
            return

        UserRole.objects.bulk_create(
            [UserRole(user_id=user.pk, role_id=role_id) for role_id in normalized_role_ids],
            ignore_conflicts=True,
        )

    def clear_user_roles(self, *, user):
        if user is None or not getattr(user, "pk", None):
            return
        UserRole.objects.filter(user_id=user.pk).delete()

    def list_active_studies(self):
        return Study.objects.filter(is_active=True, deleted=False).order_by("id")

    def list_active_sites(self, *, study_ids=()):
        queryset = Site.objects.filter(is_active=True, deleted=False)
        if study_ids:
            queryset = queryset.filter(study_id__in=study_ids)
        return queryset.order_by("id")

    def list_study_memberships_for_user(self, user):
        if user is None or not getattr(user, "pk", None):
            return StudyMembership.objects.none()
        return StudyMembership.objects.filter(user_id=user.pk, deleted=False).order_by("study_id")

    def list_site_memberships_for_user(self, user):
        if user is None or not getattr(user, "pk", None):
            return StudySiteMembership.objects.none()
        return StudySiteMembership.objects.filter(user_id=user.pk, deleted=False).order_by("study_id", "site_id")

    def list_study_membership_role_assignments_for_user(self, user):
        if user is None or not getattr(user, "pk", None):
            return StudyMembershipRole.objects.none()
        return (
            StudyMembershipRole.objects.select_related("study_membership", "role")
            .filter(
                study_membership__user_id=user.pk,
                study_membership__deleted=False,
                study_membership__status="ACTIVE",
                status=RoleAssignmentStatus.ACTIVE,
                role__scope_level=RoleScopeLevel.STUDY,
                role__is_active=True,
            )
            .order_by("study_membership__study_id", "role__name")
        )

    def list_site_membership_role_assignments_for_user(self, user):
        if user is None or not getattr(user, "pk", None):
            return StudySiteMembershipRole.objects.none()
        return (
            StudySiteMembershipRole.objects.select_related("study_site_membership", "role")
            .filter(
                study_site_membership__user_id=user.pk,
                study_site_membership__deleted=False,
                study_site_membership__status="ACTIVE",
                status=RoleAssignmentStatus.ACTIVE,
                role__scope_level=RoleScopeLevel.STUDY_SITE,
                role__is_active=True,
            )
            .order_by("study_site_membership__study_id", "study_site_membership__site_id", "role__name")
        )

    def list_accessible_studies_for_user(self, user, *, search_query=""):
        queryset = self.list_active_studies()
        if search_query:
            normalized_search_query = search_query.strip()
            if normalized_search_query:
                matched_ids = self.sonic_search_adapter.search_study_ids(query=normalized_search_query)
                if matched_ids is None:
                    queryset = queryset.filter(
                        Q(code__icontains=normalized_search_query)
                        | Q(name__icontains=normalized_search_query)
                        | Q(sponsor__icontains=normalized_search_query)
                        | Q(description__icontains=normalized_search_query),
                    ).order_by("id")
                elif matched_ids:
                    queryset = queryset.filter(pk__in=matched_ids).order_by("id")
                else:
                    queryset = queryset.none()

        if user.is_superuser:
            return queryset

        study_membership_ids = self.list_study_memberships_for_user(user).values_list("study_id", flat=True)
        site_membership_study_ids = self.list_site_memberships_for_user(user).values_list("study_id", flat=True)
        return queryset.filter(Q(pk__in=study_membership_ids) | Q(pk__in=site_membership_study_ids))

    def list_accessible_sites_for_user(self, user, *, study_ids=(), search_query=""):
        queryset = self.list_active_sites(study_ids=study_ids)
        if search_query:
            normalized_search_query = search_query.strip()
            if normalized_search_query:
                matched_ids = self.sonic_search_adapter.search_site_ids(query=normalized_search_query)
                if matched_ids is None:
                    queryset = queryset.filter(
                        Q(code__icontains=normalized_search_query)
                        | Q(name__icontains=normalized_search_query)
                        | Q(investigator__username__icontains=normalized_search_query)
                        | Q(investigator__first_name__icontains=normalized_search_query)
                        | Q(investigator__last_name__icontains=normalized_search_query)
                        | Q(investigator__display_name__icontains=normalized_search_query),
                    ).order_by("id")
                elif matched_ids:
                    queryset = queryset.filter(pk__in=matched_ids).order_by("id")
                else:
                    queryset = queryset.none()

        if user.is_superuser:
            return queryset

        allowed_study_ids = self.list_study_memberships_for_user(user).values_list("study_id", flat=True)
        allowed_site_ids = self.list_site_memberships_for_user(user).values_list("site_id", flat=True)
        return queryset.filter(Q(study_id__in=allowed_study_ids) | Q(pk__in=allowed_site_ids)).distinct()

    def set_user_study_memberships(self, *, user, study_ids, actor_user_id, role_ids_by_study_id=None):
        if user is None or not getattr(user, "pk", None):
            return

        normalized_study_ids = []
        seen_study_ids = set()
        for study_id in study_ids or ():
            normalized_study_id = str(study_id).strip()
            if not normalized_study_id or normalized_study_id in seen_study_ids or not normalized_study_id.isdigit():
                continue
            seen_study_ids.add(normalized_study_id)
            normalized_study_ids.append(int(normalized_study_id))

        StudyMembership.objects.filter(user_id=user.pk).delete()
        if not normalized_study_ids:
            return

        now = timezone.now()
        StudyMembership.objects.bulk_create(
            [
                StudyMembership(
                    user_id=user.pk,
                    study_id=study_id,
                    role="member",
                    is_global_role=False,
                    deleted=False,
                    created_at=now,
                    updated_at=now,
                    created_by_id=actor_user_id,
                    updated_by_id=actor_user_id,
                )
                for study_id in normalized_study_ids
            ],
            ignore_conflicts=True,
        )
        self._set_user_study_membership_roles(
            user=user,
            study_ids=normalized_study_ids,
            role_ids_by_study_id=role_ids_by_study_id or {},
            actor_user_id=actor_user_id,
        )

    def set_user_site_memberships(self, *, user, site_ids, allowed_study_ids, actor_user_id, role_ids_by_site_id=None):
        if user is None or not getattr(user, "pk", None):
            return

        normalized_site_ids = []
        seen_site_ids = set()
        for site_id in site_ids or ():
            normalized_site_id = str(site_id).strip()
            if not normalized_site_id or normalized_site_id in seen_site_ids or not normalized_site_id.isdigit():
                continue
            seen_site_ids.add(normalized_site_id)
            normalized_site_ids.append(int(normalized_site_id))

        StudySiteMembership.objects.filter(user_id=user.pk).delete()
        if not normalized_site_ids:
            return

        normalized_study_ids = []
        for study_id in allowed_study_ids or ():
            normalized_study_id = str(study_id).strip()
            if normalized_study_id.isdigit():
                normalized_study_ids.append(int(normalized_study_id))

        eligible_sites = list(self.list_active_sites(study_ids=normalized_study_ids).filter(pk__in=normalized_site_ids))
        if not eligible_sites:
            return

        now = timezone.now()
        StudySiteMembership.objects.bulk_create(
            [
                StudySiteMembership(
                    user_id=user.pk,
                    study_id=site.study_id,
                    site_id=site.pk,
                    deleted=False,
                    created_at=now,
                    updated_at=now,
                    created_by_id=actor_user_id,
                    updated_by_id=actor_user_id,
                )
                for site in eligible_sites
            ],
            ignore_conflicts=True,
        )
        self._set_user_site_membership_roles(
            user=user,
            sites=eligible_sites,
            role_ids_by_site_id=role_ids_by_site_id or {},
            actor_user_id=actor_user_id,
        )

    def _set_user_study_membership_roles(self, *, user, study_ids, role_ids_by_study_id, actor_user_id):
        memberships = {
            int(membership.study_id): membership
            for membership in StudyMembership.objects.filter(user_id=user.pk, study_id__in=study_ids, deleted=False)
        }
        role_ids = self._normalize_role_map_values(role_ids_by_study_id)
        valid_roles = {
            (int(role.study_id), int(role.pk)): role
            for role in Role.objects.filter(
                pk__in=role_ids,
                study_id__in=study_ids,
                scope_level=RoleScopeLevel.STUDY,
                is_active=True,
            )
        }
        now = timezone.now()
        assignments = []
        for raw_study_id, raw_role_id in (role_ids_by_study_id or {}).items():
            study_id = self._to_int(raw_study_id)
            role_id = self._to_int(raw_role_id)
            if study_id is None or role_id is None:
                continue
            membership = memberships.get(study_id)
            if membership is None or (study_id, role_id) not in valid_roles:
                continue
            assignments.append(
                StudyMembershipRole(
                    study_membership_id=membership.pk,
                    role_id=role_id,
                    assigned_at=now,
                    assigned_by_id=actor_user_id,
                    status=RoleAssignmentStatus.ACTIVE,
                )
            )
        if assignments:
            StudyMembershipRole.objects.bulk_create(assignments, ignore_conflicts=True)

    def _set_user_site_membership_roles(self, *, user, sites, role_ids_by_site_id, actor_user_id):
        site_ids = [int(site.pk) for site in sites]
        memberships = {
            int(membership.site_id): membership
            for membership in StudySiteMembership.objects.filter(user_id=user.pk, site_id__in=site_ids, deleted=False)
        }
        study_id_by_site_id = {int(site.pk): int(site.study_id) for site in sites}
        role_ids = self._normalize_role_map_values(role_ids_by_site_id)
        valid_roles = {
            (int(role.study_id), int(role.pk)): role
            for role in Role.objects.filter(
                pk__in=role_ids,
                study_id__in=set(study_id_by_site_id.values()),
                scope_level=RoleScopeLevel.STUDY_SITE,
                is_active=True,
            )
        }
        now = timezone.now()
        assignments = []
        for raw_site_id, raw_role_id in (role_ids_by_site_id or {}).items():
            site_id = self._to_int(raw_site_id)
            role_id = self._to_int(raw_role_id)
            if site_id is None or role_id is None:
                continue
            membership = memberships.get(site_id)
            study_id = study_id_by_site_id.get(site_id)
            if membership is None or study_id is None or (study_id, role_id) not in valid_roles:
                continue
            assignments.append(
                StudySiteMembershipRole(
                    study_site_membership_id=membership.pk,
                    role_id=role_id,
                    assigned_at=now,
                    assigned_by_id=actor_user_id,
                    status=RoleAssignmentStatus.ACTIVE,
                )
            )
        if assignments:
            StudySiteMembershipRole.objects.bulk_create(assignments, ignore_conflicts=True)

    @staticmethod
    def _normalize_role_map_values(role_ids_by_scope):
        role_ids = []
        for role_id in (role_ids_by_scope or {}).values():
            normalized_role_id = DjangoIdentityUserRepository._to_int(role_id)
            if normalized_role_id is not None:
                role_ids.append(normalized_role_id)
        return role_ids

    @staticmethod
    def _to_int(value):
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return None

    def get_latest_user_deleted_event(self, *, user_id):
        return (
            AuditEvent.objects.filter(
                deleted=False,
                action=AuditEventAction.IDENTITY_USER_DELETED,
                object_type=AuditEventObjectType.IDENTITY_USER,
                object_id=str(user_id),
            )
            .order_by("-created_at")
            .first()
        )

    @staticmethod
    def _apply_user_filters(queryset, *, exclude_user_id, deleted):
        if deleted is not None:
            queryset = queryset.filter(deleted=deleted)
        if exclude_user_id is not None:
            queryset = queryset.exclude(pk=exclude_user_id)
        return queryset

    @staticmethod
    def _normalize_ids(values):
        normalized_ids = []
        seen_ids = set()
        for value in values or ():
            normalized_value = str(value).strip()
            if not normalized_value or normalized_value in seen_ids or not normalized_value.isdigit():
                continue
            seen_ids.add(normalized_value)
            normalized_ids.append(int(normalized_value))
        return normalized_ids
