from django.test import TestCase

from apps.identity.application.services.default_role_seed import seed_default_role_permissions
from apps.identity.models import IdentityPermission, Role


class DefaultRolePermissionSeedTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed_default_role_permissions(using="default")

    def test_seed_creates_matrix_edc_roles_and_permissions(self):
        self.assertEqual(Role.objects.filter(study_id=1).count(), 5)
        self.assertTrue(
            IdentityPermission.objects.filter(
                app_label="edc",
                codename="CRF.ENTER",
            ).exists()
        )
        self.assertTrue(
            IdentityPermission.objects.filter(
                app_label="edc",
                codename="DATA.LOCK",
            ).exists()
        )

        data_manager_role = Role.objects.get(study_id=1, name="Data Manager")
        self.assertTrue(
            data_manager_role.permissions.filter(
                app_label="edc",
                codename="DATA.LOCK",
            ).exists()
        )
        self.assertFalse(
            data_manager_role.permissions.filter(
                app_label="edc",
                codename="USER_ACCESS.MANAGE",
            ).exists()
        )

        study_admin_role = Role.objects.get(
            study_id=1,
            name="Study Admin",
        )
        self.assertTrue(
            study_admin_role.permissions.filter(
                app_label="edc",
                codename="USER_ACCESS.MANAGE",
            ).exists()
        )
