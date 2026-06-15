from django.test import SimpleTestCase

from apps.identity.application.permissions import (
    ALL_PERMISSION_DEFINITIONS,
    APP_PERMISSION_DEFINITIONS,
    EDC_PERMISSION_DEFINITIONS,
)


class PermissionRegistryTests(SimpleTestCase):
    def test_app_permission_registry_has_unique_codes(self):
        permission_codes = [
            definition.permission_code
            for definition in APP_PERMISSION_DEFINITIONS
        ]

        self.assertEqual(len(permission_codes), len(set(permission_codes)))

    def test_app_permission_registry_contains_used_permission_codes(self):
        permission_codes = {
            definition.permission_code
            for definition in APP_PERMISSION_DEFINITIONS
        }

        self.assertTrue(
            {
                "dashboard.view_dashboard",
                "identity.view_user_list",
                "identity.update_user",
                "site.view_site_membership_list",
                "study.manage_crf_template",
                "study.update_study_field_name",
                "subject.verify_form",
                "reconcile.view_internal_query_thread",
            }.issubset(permission_codes)
        )

    def test_seed_registry_includes_edc_permissions(self):
        edc_permission_codes = {
            definition.codename
            for definition in EDC_PERMISSION_DEFINITIONS
        }
        all_permission_codes = {
            definition.permission_code
            for definition in ALL_PERMISSION_DEFINITIONS
        }

        self.assertIn("DATA.LOCK", edc_permission_codes)
        self.assertIn("DATA.LOCK", all_permission_codes)
