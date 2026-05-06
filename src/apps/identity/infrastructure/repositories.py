from django.contrib.auth.models import Group
from django.db.models import Q
from django.utils import timezone

from apps.audit.infrastructure.persistence.models import AuditEvent
from apps.identity.infrastructure.sonic import SonicSearchAdapter
from apps.identity.models import Role, StudyMembership, StudySiteMembership, User, UserRole
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

    def get_user_with_groups(self, *, user_id):
        return User.objects.prefetch_related("groups").filter(pk=user_id).first()

    def list_users(self, *, order_by=()):
        return User.objects.filter(deleted=False).order_by(*order_by)

    def get_user_for_detail(self, *, user_id, include_deleted=False):
        queryset = User.objects.prefetch_related("groups").filter(pk=user_id)
        if not include_deleted:
            queryset = queryset.filter(deleted=False)
        return queryset.first()

    def reload_user_with_groups(self, user):
        return User.objects.prefetch_related("groups").get(pk=user.pk)

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

    def list_groups_by_ids(self, group_ids):
        return Group.objects.filter(pk__in=group_ids).order_by("name")

    def list_groups_by_names(self, group_names):
        return Group.objects.filter(name__in=group_names).order_by("name")

    def list_groups(self):
        return Group.objects.order_by("name")

    def list_roles(self):
        return Role.objects.order_by("name")

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

    def list_accessible_studies_for_user(self, user, *, search_query=""):
        queryset = self.list_active_studies()
        if search_query:
            normalized_search_query = search_query.strip()
            if normalized_search_query:
                matched_ids = self.sonic_search_adapter.search_study_ids(query=normalized_search_query)
                if matched_ids:
                    queryset = queryset.filter(pk__in=matched_ids).order_by("id")

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
                if matched_ids:
                    queryset = queryset.filter(pk__in=matched_ids).order_by("id")

        if user.is_superuser:
            return queryset

        allowed_study_ids = self.list_study_memberships_for_user(user).values_list("study_id", flat=True)
        allowed_site_ids = self.list_site_memberships_for_user(user).values_list("site_id", flat=True)
        return queryset.filter(study_id__in=allowed_study_ids, pk__in=allowed_site_ids)

    def set_user_study_memberships(self, *, user, study_ids, actor_user_id):
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

    def set_user_site_memberships(self, *, user, site_ids, allowed_study_ids, actor_user_id):
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

        eligible_sites = self.list_active_sites(study_ids=normalized_study_ids).filter(pk__in=normalized_site_ids)
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
