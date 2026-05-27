from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.audit.infrastructure.persistence.models import AuditEvent
from apps.identity.infrastructure.auth.authorization import (
    AccessControlMutationService,
    AuthorizationService,
    ResourceContext,
)
from apps.identity.models import (
    DelegationOfAuthority,
    DelegationTask,
    MembershipStatus,
    Role,
    RoleAssignmentStatus,
    RoleScopeLevel,
    StudyMembership,
    StudyMembershipRole,
    StudySiteMembership,
    StudySiteMembershipRole,
    TrainingCompletion,
    TrainingRequirement,
    User,
)
from apps.study.models import Site, Study


class AuthorizationServiceTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.content_type, _ = ContentType.objects.get_or_create(
            app_label="edc",
            model="permissioncode",
        )
        self.permissions = {
            code: Permission.objects.get_or_create(
                content_type=self.content_type,
                codename=code,
                defaults={"name": code},
            )[0]
            for code in (
                "SUBJECT.VIEW",
                "CRF.VIEW",
                "CRF.UPDATE",
                "CRF.SUBMIT",
                "QUERY.CREATE",
                "QUERY.RESPOND",
                "QUERY.CLOSE",
                "CASEBOOK.SIGN",
            )
        }
        self.user = User.objects.create_user(username="scope-user", password="pw")
        self.study_a = self._create_study("A")
        self.study_b = self._create_study("B")
        self.hcm_a = self._create_site(self.study_a, "HCM01")
        self.hn_a = self._create_site(self.study_a, "HN01")
        self.hcm_b = self._create_site(self.study_b, "HCM01")
        self.service = AuthorizationService()

    def test_user_has_no_membership_denies_study_resource(self):
        result = self._can("CRF.VIEW", self.study_a, self.hcm_a)

        self.assertFalse(result.is_allowed)
        self.assertEqual(result.deny_reason_code, "NO_ACTIVE_STUDY_MEMBERSHIP")

    def test_study_membership_without_role_denies(self):
        self._study_membership(self.user, self.study_a)

        result = self._can("CRF.VIEW", self.study_a, self.hcm_a)

        self.assertFalse(result.is_allowed)
        self.assertEqual(result.deny_reason_code, "ROLE_NOT_ASSIGNED")

    def test_study_site_membership_without_role_denies(self):
        self._study_membership(self.user, self.study_a)
        self._site_membership(self.user, self.study_a, self.hcm_a)

        result = self._can("CRF.VIEW", self.study_a, self.hcm_a)

        self.assertFalse(result.is_allowed)
        self.assertEqual(result.deny_reason_code, "ROLE_NOT_ASSIGNED")

    def test_data_coordinator_is_limited_to_exact_study_site(self):
        self._assign_site_role(self.user, self.study_a, self.hcm_a, "DATA_COORDINATOR", ["CRF.UPDATE"])

        self.assertTrue(self._can("CRF.UPDATE", self.study_a, self.hcm_a).is_allowed)
        self.assertEqual(self._can("CRF.UPDATE", self.study_a, self.hn_a).deny_reason_code, "ROLE_NOT_ASSIGNED")
        self.assertEqual(self._can("CRF.UPDATE", self.study_b, self.hcm_b).deny_reason_code, "NO_ACTIVE_STUDY_MEMBERSHIP")

    def test_same_physical_site_code_does_not_leak_role_between_studies(self):
        self._assign_site_role(self.user, self.study_a, self.hcm_a, "PI", ["CASEBOOK.SIGN"])
        self._assign_site_role(self.user, self.study_b, self.hcm_b, "DATA_COORDINATOR", ["CRF.UPDATE"])

        self.assertTrue(self._can("CASEBOOK.SIGN", self.study_a, self.hcm_a).is_allowed)
        self.assertTrue(self._can("CRF.UPDATE", self.study_b, self.hcm_b).is_allowed)
        self.assertEqual(self._can("CASEBOOK.SIGN", self.study_b, self.hcm_b).deny_reason_code, "PERMISSION_NOT_GRANTED")

    def test_cra_monitor_only_accesses_assigned_study_sites(self):
        self._assign_site_role(self.user, self.study_a, self.hcm_a, "CRA_MONITOR", ["CRF.VIEW", "QUERY.CREATE"])
        self._assign_site_role(self.user, self.study_b, self.hcm_b, "CRA_MONITOR", ["CRF.VIEW", "QUERY.CREATE"])

        self.assertTrue(self._can("QUERY.CREATE", self.study_a, self.hcm_a).is_allowed)
        self.assertTrue(self._can("CRF.VIEW", self.study_b, self.hcm_b).is_allowed)
        self.assertEqual(self._can("QUERY.CREATE", self.study_a, self.hn_a).deny_reason_code, "ROLE_NOT_ASSIGNED")

    def test_study_level_data_manager_applies_within_study_only(self):
        self._assign_study_role(self.user, self.study_a, "DATA_MANAGER", ["CRF.VIEW"])

        self.assertTrue(self._can("CRF.VIEW", self.study_a, self.hcm_a).is_allowed)
        self.assertTrue(self._can("CRF.VIEW", self.study_a, self.hn_a).is_allowed)
        self.assertEqual(self._can("CRF.VIEW", self.study_b, self.hcm_b).deny_reason_code, "NO_ACTIVE_STUDY_MEMBERSHIP")

    def test_study_site_role_cannot_be_assigned_to_study_membership(self):
        membership = self._study_membership(self.user, self.study_a)
        role = self._role(self.study_a, "DATA_COORDINATOR", RoleScopeLevel.STUDY_SITE, ["CRF.UPDATE"])

        with self.assertRaises(ValidationError):
            StudyMembershipRole.objects.create(
                study_membership=membership,
                role=role,
                assigned_at=self.now,
            )

    def test_study_role_cannot_be_assigned_to_study_site_membership(self):
        self._study_membership(self.user, self.study_a)
        membership = self._site_membership(self.user, self.study_a, self.hcm_a)
        role = self._role(self.study_a, "DATA_MANAGER", RoleScopeLevel.STUDY, ["CRF.VIEW"])

        with self.assertRaises(ValidationError):
            StudySiteMembershipRole.objects.create(
                study_site_membership=membership,
                role=role,
                assigned_at=self.now,
            )

    def test_revoked_membership_denies(self):
        self._assign_site_role(self.user, self.study_a, self.hcm_a, "DATA_COORDINATOR", ["CRF.UPDATE"])
        StudyMembership.objects.filter(user=self.user, study_id=self.study_a.pk).update(status=MembershipStatus.REVOKED)

        self.assertEqual(self._can("CRF.UPDATE", self.study_a, self.hcm_a).deny_reason_code, "NO_ACTIVE_STUDY_MEMBERSHIP")

    def test_expired_membership_denies(self):
        membership = self._study_membership(self.user, self.study_a)
        membership.valid_to = self.now - timezone.timedelta(days=1)
        membership.save(update_fields=["valid_to"])

        result = self._can("CRF.VIEW", self.study_a, self.hcm_a)

        self.assertEqual(result.deny_reason_code, "NO_ACTIVE_STUDY_MEMBERSHIP")

    def test_revoked_role_assignment_denies(self):
        assignment = self._assign_site_role(self.user, self.study_a, self.hcm_a, "DATA_COORDINATOR", ["CRF.UPDATE"])
        assignment.status = RoleAssignmentStatus.REVOKED
        assignment.save(update_fields=["status"])

        self.assertEqual(self._can("CRF.UPDATE", self.study_a, self.hcm_a).deny_reason_code, "ROLE_NOT_ASSIGNED")

    def test_permission_granted_through_group_resolves(self):
        self._assign_site_role(
            self.user,
            self.study_a,
            self.hcm_a,
            "DATA_COORDINATOR",
            [],
            group_permissions=["CRF.UPDATE"],
        )

        self.assertTrue(self._can("CRF.UPDATE", self.study_a, self.hcm_a).is_allowed)

    def test_permission_granted_directly_to_role_resolves(self):
        self._assign_site_role(self.user, self.study_a, self.hcm_a, "DATA_COORDINATOR", ["CRF.UPDATE"])

        self.assertTrue(self._can("CRF.UPDATE", self.study_a, self.hcm_a).is_allowed)

    def test_locked_form_denies_update_even_when_permission_exists(self):
        self._assign_site_role(self.user, self.study_a, self.hcm_a, "DATA_COORDINATOR", ["CRF.UPDATE"])

        result = self._can("CRF.UPDATE", self.study_a, self.hcm_a, is_locked=True)

        self.assertEqual(result.deny_reason_code, "FORM_LOCKED")

    def test_frozen_form_denies_update(self):
        self._assign_site_role(self.user, self.study_a, self.hcm_a, "DATA_COORDINATOR", ["CRF.UPDATE"])

        result = self._can("CRF.UPDATE", self.study_a, self.hcm_a, is_frozen=True)

        self.assertEqual(result.deny_reason_code, "FORM_FROZEN")

    def test_signed_form_denies_update(self):
        self._assign_site_role(self.user, self.study_a, self.hcm_a, "DATA_COORDINATOR", ["CRF.UPDATE"])

        result = self._can("CRF.UPDATE", self.study_a, self.hcm_a, is_signed=True)

        self.assertEqual(result.deny_reason_code, "FORM_SIGNED")

    def test_delegation_required_blocks_until_active_delegation_exists(self):
        self._assign_site_role(self.user, self.study_a, self.hcm_a, "DATA_COORDINATOR", ["CRF.SUBMIT"])
        DelegationTask.objects.create(
            code="DATA_ENTRY",
            name="Data entry",
            required_permission_code="CRF.SUBMIT",
        )

        self.assertEqual(self._can("CRF.SUBMIT", self.study_a, self.hcm_a).deny_reason_code, "DELEGATION_REQUIRED")

        DelegationOfAuthority.objects.create(
            study_site_id=self.hcm_a.pk,
            user=self.user,
            task_code="DATA_ENTRY",
            delegated_by_user_id=self.user.pk,
            status="ACTIVE",
            created_at=self.now,
        )

        self.assertTrue(self._can("CRF.SUBMIT", self.study_a, self.hcm_a).is_allowed)

    def test_training_required_blocks_until_non_expired_completion_exists(self):
        self._assign_site_role(self.user, self.study_a, self.hcm_a, "DATA_COORDINATOR", ["CRF.UPDATE"])
        TrainingRequirement.objects.create(
            study_id=self.study_a.pk,
            permission_code="CRF.UPDATE",
            training_code="EDC_BASICS",
        )

        self.assertEqual(self._can("CRF.UPDATE", self.study_a, self.hcm_a).deny_reason_code, "TRAINING_REQUIRED")

        TrainingCompletion.objects.create(
            user=self.user,
            study_id=self.study_a.pk,
            training_code="EDC_BASICS",
            completed_at=self.now,
            expires_at=self.now - timezone.timedelta(days=1),
        )
        self.assertEqual(self._can("CRF.UPDATE", self.study_a, self.hcm_a).deny_reason_code, "TRAINING_REQUIRED")

        TrainingCompletion.objects.create(
            user=self.user,
            study_id=self.study_a.pk,
            training_code="EDC_BASICS",
            completed_at=self.now,
            expires_at=self.now + timezone.timedelta(days=1),
        )
        self.assertTrue(self._can("CRF.UPDATE", self.study_a, self.hcm_a).is_allowed)

    def test_query_workflow_permissions_follow_role_matrix(self):
        self._assign_site_role(self.user, self.study_a, self.hcm_a, "DATA_COORDINATOR", ["QUERY.RESPOND"])
        self.assertTrue(self._can("QUERY.RESPOND", self.study_a, self.hcm_a).is_allowed)
        self.assertEqual(self._can("QUERY.CLOSE", self.study_a, self.hcm_a).deny_reason_code, "PERMISSION_NOT_GRANTED")

        cra = User.objects.create_user(username="cra-user", password="pw")
        self._assign_site_role(cra, self.study_a, self.hcm_a, "CRA_MONITOR", ["QUERY.CREATE", "QUERY.CLOSE"])
        self.assertTrue(self._can("QUERY.CREATE", self.study_a, self.hcm_a, user=cra).is_allowed)
        self.assertTrue(self._can("QUERY.CLOSE", self.study_a, self.hcm_a, user=cra).is_allowed)
        self.assertEqual(self._can("QUERY.RESPOND", self.study_a, self.hcm_a, user=cra).deny_reason_code, "PERMISSION_NOT_GRANTED")

    def test_assign_role_writes_audit_event(self):
        membership = self._study_membership(self.user, self.study_a)
        role = self._role(self.study_a, "DATA_MANAGER", RoleScopeLevel.STUDY, ["CRF.VIEW"])

        AccessControlMutationService().assign_study_role(
            study_membership_id=membership.pk,
            role_id=role.pk,
            actor_user_id=self.user.pk,
        )

        self.assertTrue(AuditEvent.objects.filter(action="identity.role_assigned").exists())

    def _can(self, permission_code, study, site, user=None, **context_overrides):
        context = ResourceContext(
            study_id=study.pk,
            study_site_id=site.pk,
            **context_overrides,
        )
        return self.service.can_perform(
            user_id=(user or self.user).pk,
            permission_code=permission_code,
            resource_context=context,
        )

    def _assign_study_role(self, user, study, role_code, permissions):
        membership = self._study_membership(user, study)
        role = self._role(study, role_code, RoleScopeLevel.STUDY, permissions)
        return StudyMembershipRole.objects.create(
            study_membership=membership,
            role=role,
            assigned_at=self.now,
        )

    def _assign_site_role(self, user, study, site, role_code, permissions, group_permissions=None):
        self._study_membership(user, study)
        membership = self._site_membership(user, study, site)
        role = self._role(study, role_code, RoleScopeLevel.STUDY_SITE, permissions)
        if group_permissions:
            group = Group.objects.create(name=f"{role_code}-{study.pk}-{site.pk}")
            group.permissions.add(*(self.permissions[permission_code] for permission_code in group_permissions))
            role.groups.add(group)
        return StudySiteMembershipRole.objects.create(
            study_site_membership=membership,
            role=role,
            assigned_at=self.now,
        )

    def _role(self, study, code, scope_level, permissions):
        role, _ = Role.objects.update_or_create(
            study_id=study.pk,
            code=code,
            scope_level=scope_level,
            version_no=1,
            defaults={
                "name": code.replace("_", " ").title(),
                "description": "",
                "is_active": True,
            },
        )
        role.permissions.add(*(self.permissions[permission_code] for permission_code in permissions))
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

    def _create_study(self, code):
        return Study.objects.create(
            created_at=self.now,
            updated_at=self.now,
            code=f"STUDY-{code}",
            name=f"Study {code}",
            description="",
            is_active=True,
        )

    def _create_site(self, study, code):
        return Site.objects.create(
            created_at=self.now,
            updated_at=self.now,
            code=code,
            name=f"Site {code}",
            study=study,
            is_active=True,
        )
