from django.db.models import Q
from django.utils import timezone

from apps.identity.infrastructure.persistence.models import (
    MembershipStatus,
    Role,
    RoleAssignmentStatus,
    StudyMembershipRole,
    StudySiteMembershipRole,
    User,
)


class DjangoIdentityRoleScopeRepository:
    @staticmethod
    def list_study_role_options(*, study_id: int) -> list[dict]:
        return [
            {
                "id": int(role.pk),
                "code": str(role.code or ""),
                "name": str(role.name or ""),
                "scope_level": str(role.scope_level or ""),
                "permission_codes": tuple(
                    sorted(permission.permission_code for permission in role.permissions.all())
                ),
            }
            for role in Role.objects.filter(study_id=study_id, is_active=True)
            .prefetch_related("permissions")
            .order_by("name", "id")
        ]

    @classmethod
    def user_has_any_active_role_ids(
        cls,
        *,
        user_id: int,
        study_id: int,
        site_id: int | None,
        role_ids: tuple[int, ...],
    ) -> bool:
        if not role_ids:
            return True
        if User.objects.filter(pk=user_id, is_active=True, is_superuser=True).exists():
            return True
        now = timezone.now()
        membership_window = Q(study_membership__valid_from__isnull=True) | Q(
            study_membership__valid_from__lte=now
        )
        membership_window &= Q(study_membership__valid_to__isnull=True) | Q(
            study_membership__valid_to__gte=now
        )
        if StudyMembershipRole.objects.filter(
            membership_window,
            study_membership__user_id=user_id,
            study_membership__study_id=study_id,
            study_membership__deleted=False,
            study_membership__status=MembershipStatus.ACTIVE,
            status=RoleAssignmentStatus.ACTIVE,
            revoked_at__isnull=True,
            role_id__in=role_ids,
            role__study_id=study_id,
            role__is_active=True,
        ).exists():
            return True
        if site_id is None:
            return False
        site_window = Q(study_site_membership__valid_from__isnull=True) | Q(
            study_site_membership__valid_from__lte=now
        )
        site_window &= Q(study_site_membership__valid_to__isnull=True) | Q(
            study_site_membership__valid_to__gte=now
        )
        return StudySiteMembershipRole.objects.filter(
            site_window,
            study_site_membership__user_id=user_id,
            study_site_membership__study_id=study_id,
            study_site_membership__site_id=site_id,
            study_site_membership__deleted=False,
            study_site_membership__status=MembershipStatus.ACTIVE,
            status=RoleAssignmentStatus.ACTIVE,
            revoked_at__isnull=True,
            role_id__in=role_ids,
            role__study_id=study_id,
            role__is_active=True,
        ).exists()

    @classmethod
    def user_has_any_active_role_codes(
        cls,
        *,
        user_id: int,
        study_id: int,
        site_id: int | None,
        role_codes: tuple[str, ...],
    ) -> bool:
        normalized_codes = tuple(
            dict.fromkeys(
                str(code or "").strip().upper()
                for code in role_codes
                if str(code or "").strip()
            )
        )
        if not normalized_codes:
            return True
        role_ids = tuple(
            Role.objects.filter(
                study_id=study_id,
                is_active=True,
                code__in=normalized_codes,
            ).values_list("id", flat=True)
        )
        if not role_ids:
            return False
        return cls.user_has_any_active_role_ids(
            user_id=user_id,
            study_id=study_id,
            site_id=site_id,
            role_ids=role_ids,
        )


__all__ = ["DjangoIdentityRoleScopeRepository"]
