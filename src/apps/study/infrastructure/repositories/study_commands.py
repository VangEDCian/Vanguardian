from django.db.models import Q
from django.utils import timezone

from apps.identity.infrastructure.persistence.models import StudyMembership, User
from apps.study.infrastructure.persistence.models import Site, SiteMembership, Study


class DjangoStudyCommandRepository:
    def get_study(self, *, study_id):
        return Study.objects.filter(pk=study_id, deleted=False).first()

    def study_code_exists(self, *, code, exclude_id=None):
        queryset = Study.objects.filter(code=code.strip(), deleted=False)
        if exclude_id is not None:
            queryset = queryset.exclude(pk=exclude_id)
        return queryset.exists()

    def create_study(
        self,
        *,
        code,
        name,
        sponsor,
        description,
        start_date,
        end_date,
        is_active,
        actor_user_id,
    ):
        now = timezone.now()
        return Study.objects.create(
            code=code.strip(),
            name=name.strip(),
            sponsor=sponsor.strip(),
            description=description.strip(),
            start_date=start_date,
            end_date=end_date,
            is_active=is_active,
            created_at=now,
            updated_at=now,
            created_by_id=actor_user_id,
            updated_by_id=actor_user_id,
        )

    def save_study(self, study):
        study.save()
        return study

    def touch_study(self, study, *, actor_user_id):
        study.updated_at = timezone.now()
        study.updated_by_id = actor_user_id
        return study

    def create_site(
        self,
        *,
        code,
        name,
        investigator_id,
        study_id,
        is_active,
        actor_user_id,
    ):
        now = timezone.now()
        return Site.objects.create(
            code=code.strip(),
            name=name.strip(),
            investigator_id=investigator_id,
            study_id=study_id,
            is_active=is_active,
            created_at=now,
            updated_at=now,
            created_by_id=actor_user_id,
            updated_by_id=actor_user_id,
        )

    def site_code_exists(self, *, study_id, code):
        return Site.objects.filter(
            study_id=study_id,
            code=code.strip(),
            deleted=False,
        ).exists()

    def get_site(self, *, site_id):
        return Site.objects.filter(pk=site_id, deleted=False).first()

    def site_exists(self, *, site_id):
        return Site.objects.filter(pk=site_id, deleted=False).exists()

    def save_site(self, site):
        site.save()
        return site

    def touch_site(self, site, *, actor_user_id):
        site.updated_at = timezone.now()
        site.updated_by_id = actor_user_id
        return site

    def get_user(self, *, user_id):
        return User.objects.filter(pk=user_id, deleted=False).first()

    def site_membership_exists(self, *, site_id, user_id):
        return SiteMembership.objects.filter(
            site_id=site_id,
            user_id=user_id,
            deleted=False,
        ).exists()

    def list_users_for_study_or_site_membership(self, *, study_id, site_id, search_query=""):
        study_member_user_ids = StudyMembership.objects.filter(
            study_id=study_id,
            deleted=False,
        ).values_list("user_id", flat=True)
        site_member_user_ids = SiteMembership.objects.filter(
            site_id=site_id,
            deleted=False,
        ).values_list("user_id", flat=True)

        queryset = User.objects.filter(
            deleted=False,
        ).filter(
            Q(pk__in=study_member_user_ids) | Q(pk__in=site_member_user_ids),
        )

        normalized_search_query = (search_query or "").strip()
        if normalized_search_query:
            queryset = queryset.filter(
                Q(username__icontains=normalized_search_query)
                | Q(first_name__icontains=normalized_search_query)
                | Q(last_name__icontains=normalized_search_query)
                | Q(display_name__icontains=normalized_search_query)
                | Q(email__icontains=normalized_search_query),
            )

        return queryset.distinct().order_by("username", "id")

    def create_site_membership(self, *, site_id, study_id, user_id, actor_user_id):
        now = timezone.now()
        return SiteMembership.objects.create(
            site_id=site_id,
            study_id=study_id,
            user_id=user_id,
            created_at=now,
            updated_at=now,
            created_by_id=actor_user_id,
            updated_by_id=actor_user_id,
        )

    def get_site_membership(self, *, membership_id):
        return SiteMembership.objects.filter(pk=membership_id, deleted=False).first()

    def save_site_membership(self, membership):
        membership.save()
        return membership

    def touch_site_membership(self, membership, *, actor_user_id):
        membership.updated_at = timezone.now()
        membership.updated_by_id = actor_user_id
        return membership
