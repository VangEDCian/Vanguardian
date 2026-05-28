from django.contrib.auth.models import Group, Permission
from django.test import TestCase

from apps.identity.models import Role


class DefaultRolePermissionSeedTests(TestCase):
    def test_seed_creates_matrix_edc_groups_roles_and_permissions(self):
        self.assertEqual(Group.objects.count(), 5)
        self.assertEqual(Role.objects.filter(study_id=1).count(), 5)
        self.assertTrue(
            Permission.objects.filter(
                content_type__app_label="edc",
                codename="CRF.ENTER",
            ).exists()
        )
        self.assertTrue(
            Permission.objects.filter(
                content_type__app_label="edc",
                codename="DATA.LOCK",
            ).exists()
        )

        data_manager_group = Group.objects.get(name="Data Manager")
        self.assertTrue(
            data_manager_group.permissions.filter(
                content_type__app_label="edc",
                codename="DATA.LOCK",
            ).exists()
        )
        self.assertFalse(
            data_manager_group.permissions.filter(
                content_type__app_label="edc",
                codename="USER_ACCESS.MANAGE",
            ).exists()
        )

        study_admin_role = Role.objects.get(
            study_id=1,
            name="Study Admin",
        )
        self.assertTrue(study_admin_role.groups.filter(name="Study Admin").exists())
        self.assertTrue(
            study_admin_role.permissions.filter(
                content_type__app_label="edc",
                codename="USER_ACCESS.MANAGE",
            ).exists()
        )
