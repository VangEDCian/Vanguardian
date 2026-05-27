from django.contrib.auth.models import Group, Permission
from django.test import TestCase

from apps.identity.models import Role


class DefaultRolePermissionSeedTests(TestCase):
    def test_seed_creates_default_groups_roles_and_manual_site_permissions(self):
        self.assertEqual(Group.objects.count(), 6)
        self.assertEqual(Role.objects.filter(study_id=1).count(), 6)
        self.assertTrue(
            Permission.objects.filter(
                content_type__app_label="dashboard",
                codename="view_dashboard",
            ).exists()
        )
        self.assertTrue(
            Permission.objects.filter(
                content_type__app_label="site",
                codename="view_site_membership_list",
            ).exists()
        )

        database_administrator_group = Group.objects.get(name="Database Administrator")
        self.assertTrue(
            database_administrator_group.permissions.filter(
                content_type__app_label="identity",
                codename="create_user",
            ).exists()
        )
        self.assertEqual(database_administrator_group.permissions.count(), 25)

        database_administrator_role = Role.objects.get(
            study_id=1,
            name="Database Administrator",
        )
        self.assertTrue(database_administrator_role.groups.filter(name="Database Administrator").exists())
        self.assertEqual(database_administrator_role.permissions.count(), 25)
