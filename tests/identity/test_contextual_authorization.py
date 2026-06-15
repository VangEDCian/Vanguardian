from types import SimpleNamespace

from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.identity.application.authorization import ContextualAuthorizationService
from apps.identity.infrastructure.auth.contextual_authorization import PermissionLookup, RoleMatch
from apps.identity.models import (
    IdentityPermission,
    MembershipStatus,
    Role,
    RoleAssignmentStatus,
    RoleScopeLevel,
    StudyMembership,
    StudyMembershipRole,
    StudySiteMembership,
    StudySiteMembershipRole,
    User,
)
from apps.study.models import Site, Study


class ContextualAuthorizationServiceTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.permission = IdentityPermission.objects.get_or_create(
            app_label="datacapture",
            codename="change_pageentry",
            defaults={"name": "Can change page entry"},
        )[0]
        self.view_permission = IdentityPermission.objects.get_or_create(
            app_label="datacapture",
            codename="view_pageentry",
            defaults={"name": "Can view page entry"},
        )[0]
        self.user = User.objects.create_user(username="context-user", password="pw")
        self.study_a = self._study("A")
        self.study_b = self._study("B")
        self.site_a = self._site(self.study_a, "HCM01")
        self.other_site_a = self._site(self.study_a, "HN01")
        self.same_physical_site_b = self._site(self.study_b, "HCM01")
        self.service = ContextualAuthorizationService()

    def test_study_role_direct_permission_allows_study_action(self):
        self._assign_study_role(self.user, self.study_a, "DATA_MANAGER", [self.permission])

        decision = self.service.can(self.user, "datacapture.change_pageentry", study_id=self.study_a.pk)

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.matched_scope, RoleScopeLevel.STUDY)

    def test_study_role_can_access_site_when_study_scope_allowed(self):
        self._assign_study_role(self.user, self.study_a, "DATA_MANAGER", [self.permission])

        decision = self.service.can(
            self.user,
            "datacapture.change_pageentry",
            study_id=self.study_a.pk,
            study_site_id=self.site_a.pk,
            allow_study_scope=True,
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.matched_scope, RoleScopeLevel.STUDY)

    def test_active_study_membership_without_role_assignment_denies(self):
        self._study_membership(self.user, self.study_a)

        decision = self.service.can(self.user, "datacapture.change_pageentry", study_id=self.study_a.pk)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "ROLE_NOT_ASSIGNED")

    def test_suspended_study_membership_denies(self):
        self._assign_study_role(self.user, self.study_a, "DATA_MANAGER", [self.permission])
        StudyMembership.objects.filter(user=self.user, study_id=self.study_a.pk).update(status=MembershipStatus.SUSPENDED)

        decision = self.service.can(self.user, "datacapture.change_pageentry", study_id=self.study_a.pk)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "NO_ACTIVE_STUDY_MEMBERSHIP")

    def test_expired_study_membership_denies(self):
        self._assign_study_role(self.user, self.study_a, "DATA_MANAGER", [self.permission])
        StudyMembership.objects.filter(user=self.user, study_id=self.study_a.pk).update(
            valid_to=self.now - timezone.timedelta(days=1),
        )

        decision = self.service.can(self.user, "datacapture.change_pageentry", study_id=self.study_a.pk)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "NO_ACTIVE_STUDY_MEMBERSHIP")

    def test_revoked_study_role_assignment_denies(self):
        assignment = self._assign_study_role(self.user, self.study_a, "DATA_MANAGER", [self.permission])
        assignment.status = RoleAssignmentStatus.REVOKED
        assignment.revoked_at = self.now
        assignment.save(update_fields=["status", "revoked_at"])

        decision = self.service.can(self.user, "datacapture.change_pageentry", study_id=self.study_a.pk)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "ROLE_NOT_ASSIGNED")

    def test_site_role_does_not_satisfy_study_only_action(self):
        self._assign_site_role(self.user, self.study_a, self.site_a, "SITE_COORDINATOR", [self.permission])

        decision = self.service.can(
            self.user,
            "datacapture.change_pageentry",
            study_id=self.study_a.pk,
            allow_study_scope=True,
            allow_site_scope=False,
        )

        self.assertFalse(decision.allowed)

    def test_missing_study_id_denies_context_required_action(self):
        decision = self.service.can(self.user, "datacapture.change_pageentry")

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "STUDY_CONTEXT_REQUIRED")

    def test_superuser_bypasses_permission_lookup_and_context_requirement(self):
        self.user.is_superuser = True
        self.user.save(update_fields=["is_superuser"])
        service = ContextualAuthorizationService(repository=NoPermissionLookupRepository())

        decision = service.can(self.user, "identity.permission_not_registered")

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.matched_scope, "GLOBAL")

    def test_site_role_direct_permission_allows_exact_site(self):
        self._assign_site_role(self.user, self.study_a, self.site_a, "SITE_COORDINATOR", [self.permission])

        decision = self.service.can(
            self.user,
            "datacapture.change_pageentry",
            study_id=self.study_a.pk,
            study_site_id=self.site_a.pk,
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.matched_scope, RoleScopeLevel.STUDY_SITE)

    def test_site_role_denies_other_site(self):
        self._assign_site_role(self.user, self.study_a, self.site_a, "SITE_COORDINATOR", [self.permission])

        decision = self.service.can(
            self.user,
            "datacapture.change_pageentry",
            study_id=self.study_a.pk,
            study_site_id=self.other_site_a.pk,
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "NO_ACTIVE_STUDY_SITE_MEMBERSHIP")

    def test_site_role_denies_other_study(self):
        self._assign_site_role(self.user, self.study_a, self.site_a, "SITE_COORDINATOR", [self.permission])

        decision = self.service.can(
            self.user,
            "datacapture.change_pageentry",
            study_id=self.study_b.pk,
            study_site_id=self.same_physical_site_b.pk,
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "NO_ACTIVE_STUDY_MEMBERSHIP")

    def test_same_physical_site_identity_does_not_leak_between_studies(self):
        self._assign_site_role(self.user, self.study_a, self.site_a, "SITE_COORDINATOR", [self.permission])
        self._study_membership(self.user, self.study_b)
        self._site_membership(self.user, self.study_b, self.same_physical_site_b)

        decision = self.service.can(
            self.user,
            "datacapture.change_pageentry",
            study_id=self.study_b.pk,
            study_site_id=self.same_physical_site_b.pk,
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "ROLE_NOT_ASSIGNED")

    def test_site_role_denied_when_study_site_id_missing(self):
        self._assign_site_role(self.user, self.study_a, self.site_a, "SITE_COORDINATOR", [self.permission])

        decision = self.service.can(self.user, "datacapture.change_pageentry", study_id=self.study_a.pk)

        self.assertFalse(decision.allowed)

    def test_study_role_denied_when_study_scope_not_allowed(self):
        self._assign_study_role(self.user, self.study_a, "DATA_MANAGER", [self.permission])

        decision = self.service.can(
            self.user,
            "datacapture.change_pageentry",
            study_id=self.study_a.pk,
            study_site_id=self.site_a.pk,
            allow_study_scope=False,
            allow_site_scope=True,
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "NO_ACTIVE_STUDY_SITE_MEMBERSHIP")

    def test_mismatched_study_site_context_denies(self):
        self._assign_site_role(self.user, self.study_a, self.site_a, "SITE_COORDINATOR", [self.permission])

        decision = self.service.can(
            self.user,
            "datacapture.change_pageentry",
            study_id=self.study_b.pk,
            study_site_id=self.site_a.pk,
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "INVALID_STUDY_SITE_CONTEXT")

    def _assign_study_role(self, user, study, code, permissions):
        membership = self._study_membership(user, study)
        role = self._role(study, code, RoleScopeLevel.STUDY, permissions)
        return StudyMembershipRole.objects.create(study_membership=membership, role=role, assigned_at=self.now)

    def _assign_site_role(self, user, study, site, code, permissions):
        self._study_membership(user, study)
        membership = self._site_membership(user, study, site)
        role = self._role(study, code, RoleScopeLevel.STUDY_SITE, permissions)
        return StudySiteMembershipRole.objects.create(study_site_membership=membership, role=role, assigned_at=self.now)

    def _role(self, study, code, scope_level, permissions):
        role = Role.objects.create(
            study_id=study.pk,
            code=f"{code}_{scope_level}_{study.pk}",
            name=f"{code} {scope_level} {study.pk}",
            scope_level=scope_level,
            is_active=True,
        )
        role.permissions.add(*permissions)
        return role

    def _study_membership(self, user, study):
        membership, _ = StudyMembership.objects.get_or_create(
            user=user,
            study_id=study.pk,
            defaults={
                "created_at": self.now,
                "updated_at": self.now,
                "role": "member",
                "status": MembershipStatus.ACTIVE,
            },
        )
        return membership

    def _site_membership(self, user, study, site):
        membership, _ = StudySiteMembership.objects.get_or_create(
            user=user,
            study_id=study.pk,
            site_id=site.pk,
            defaults={
                "created_at": self.now,
                "updated_at": self.now,
                "status": MembershipStatus.ACTIVE,
            },
        )
        return membership

    def _study(self, code):
        return Study.objects.create(
            created_at=self.now,
            updated_at=self.now,
            code=f"STUDY-{code}",
            name=f"Study {code}",
            description="",
            is_active=True,
        )

    def _site(self, study, code):
        return Site.objects.create(
            created_at=self.now,
            updated_at=self.now,
            code=code,
            name=f"Site {code}",
            study=study,
            is_active=True,
        )


class ContextualAuthorizationRequestCacheTests(TestCase):
    def test_repeated_can_calls_use_request_cache(self):
        request = RequestFactory().get("/subjects/")
        user = SimpleNamespace(id=7, pk=7, is_authenticated=True, is_active=True, is_superuser=False)
        repository = CountingAuthorizationRepository()
        service = ContextualAuthorizationService(repository=repository, request=request)

        first_decision = service.can(
            user,
            "datacapture.change_pageentry",
            study_id=1,
            study_site_id=10,
        )
        second_decision = service.can(
            user,
            "datacapture.change_pageentry",
            study_id=1,
            study_site_id=10,
        )

        self.assertTrue(first_decision.allowed)
        self.assertIs(first_decision, second_decision)
        self.assertEqual(repository.find_site_calls, 1)


class CountingAuthorizationRepository:
    find_site_calls = 0

    def resolve_permission(self, permission):
        return PermissionLookup(id=99, code=permission)

    def study_site_belongs_to_study(self, *, study_id, study_site_id):
        return True

    def find_study_site_role_match(self, *, user_id, study_id, study_site_id, permission_id):
        self.find_site_calls += 1
        return RoleMatch(scope=RoleScopeLevel.STUDY_SITE, role_id=123)

    def find_study_role_match(self, *, user_id, study_id, permission_id):
        return None

    def has_active_study_membership(self, *, user_id, study_id):
        return True

    def has_active_study_role_assignment(self, *, user_id, study_id):
        return False

    def has_active_study_site_membership(self, *, user_id, study_id, study_site_id):
        return True

    def has_active_study_site_role_assignment(self, *, user_id, study_id, study_site_id):
        return True

    def find_global_role_match(self, *, user_id, permission_id):
        return None


class NoPermissionLookupRepository:
    def resolve_permission(self, permission):
        raise AssertionError("superuser must not require permission lookup")
