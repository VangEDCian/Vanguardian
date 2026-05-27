from django.test import SimpleTestCase

from apps.crf.presentation.web.views.builder import CrfFormBuilderView
from apps.crf.presentation.web.views.field_update import CrfFieldUpdateView
from apps.dashboard.presentation.web.views import DashboardMainView
from apps.identity.presentation.web.views.users import (
    IdentityStudyOptionsApiView,
    IdentityStudySiteOptionsApiView,
    IdentityUserCreateView,
    IdentityUserDeleteView,
    IdentityUserDetailView,
    IdentityUserRestoreView,
    IdentityUsersView,
)
from apps.study.presentation.web.views.crf_templates import (
    StudyCrfSectionLayoutConfigImportTemplateView,
    StudyCrfTemplateFieldImportTemplateView,
    StudyCrfTemplateImportTemplateView,
)
from apps.study.presentation.web.views.site import SiteMembershipOptionsApiView
from apps.subject.presentation.web.views.verification_verify_checked import SubjectFormVerificationQueryThreadView


class PermissionProposalMappingTests(SimpleTestCase):
    def test_new_route_permissions_are_declared_on_views(self):
        expected_permissions = {
            DashboardMainView: "dashboard.view_dashboard",
            IdentityUsersView: "identity.view_user_list",
            IdentityUserCreateView: "identity.create_user",
            IdentityUserDetailView: "identity.view_user_detail",
            IdentityUserDeleteView: "identity.delete_user",
            IdentityUserRestoreView: "identity.restore_user",
            IdentityStudyOptionsApiView: "study.view_study_list",
            IdentityStudySiteOptionsApiView: ("study.view_study_list", "site.view_site_list"),
            SiteMembershipOptionsApiView: "site.view_site_membership_list",
            SubjectFormVerificationQueryThreadView: "subject.verify_form",
            CrfFormBuilderView: "study.manage_crf_template",
            CrfFieldUpdateView: "study.manage_crf_template",
            StudyCrfTemplateImportTemplateView: "study.manage_crf_template",
            StudyCrfTemplateFieldImportTemplateView: "study.manage_crf_template",
            StudyCrfSectionLayoutConfigImportTemplateView: "study.manage_crf_template",
        }

        for view_class, permission_required in expected_permissions.items():
            self.assertEqual(view_class.permission_required, permission_required)
