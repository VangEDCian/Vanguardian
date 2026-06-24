from django.test import SimpleTestCase
from django.urls import URLPattern, URLResolver, get_resolver

from apps.crf.presentation.web.views.builder import CrfFormBuilderView
from apps.crf.presentation.web.views.field_update import CrfFieldUpdateView
from apps.dashboard.presentation.web.views import DashboardMainView
from apps.datacapture.presentation.api.views.event_attestation import (
    DataCaptureEventAttestationRevokeAPIView,
    DataCaptureEventAttestationSubmitAPIView,
)
from apps.datacapture.presentation.api.views.form_instances import (
    DataCaptureFormInstanceListCreateAPIView,
)
from apps.datacapture.presentation.api.views.save_submit import (
    DataCaptureDeleteDraftAPIView,
    DataCaptureSaveAPIView,
    DataCaptureSubmitAPIView,
)
from apps.identity.application.permissions import ALL_PERMISSION_DEFINITIONS
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
    StudyCrfTemplateListView,
)
from apps.study.presentation.web.views.site import SiteMembershipOptionsApiView
from apps.study.presentation.web.views.studies import (
    StudyManageRolesView,
    StudyRoleCreateView,
    StudyRolesContextMixin,
)
from apps.subject.presentation.web.views.event_instance_files import SubjectEventInstanceFileImportView
from apps.subject.presentation.web.views.repeating_event_instance import SubjectAddRepeatingEventInstanceView
from apps.subject.presentation.web.views.verification_verify_checked import SubjectFormVerificationQueryThreadView, SubjectValidationIssueAcknowledgeView

EXPECTED_ROUTES_WITHOUT_BUSINESS_PERMISSION = {
    "",
    "robots.txt",
    "login/",
    "logout/",
    "admin/user/me/profile/",
    "admin/user/me/change-password/",
    "api/session/status",
    "first-login",
    "forgot-password/",
    "reset-password/<uidb64>/<token>/",
}


def _flatten_url_patterns(patterns, prefix=""):
    for pattern in patterns:
        route = prefix + str(pattern.pattern)
        if isinstance(pattern, URLResolver):
            yield from _flatten_url_patterns(pattern.url_patterns, route)
        elif isinstance(pattern, URLPattern):
            yield route, pattern


def _route_view_class(pattern):
    return getattr(pattern.callback, "view_class", None)


def _route_permission(pattern):
    view_class = _route_view_class(pattern)
    if view_class is not None:
        return getattr(view_class, "permission_required", None)
    return getattr(pattern.callback, "permission_required", None)


def _permission_list(permission_required):
    if isinstance(permission_required, str):
        return [permission_required] if permission_required else []
    if isinstance(permission_required, (tuple, list)):
        return list(permission_required)
    return []


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
            DataCaptureSaveAPIView: "CRF.ENTER",
            DataCaptureSubmitAPIView: "CRF.SUBMIT",
            DataCaptureDeleteDraftAPIView: "CRF.UPDATE",
            DataCaptureEventAttestationSubmitAPIView: "EVENT_CERTIFICATION.CERTIFY",
            DataCaptureEventAttestationRevokeAPIView: "EVENT_ATTESTATION.REVOKE",
            SubjectValidationIssueAcknowledgeView: "VALIDATION_ISSUE.ACKNOWLEDGE",
            StudyRolesContextMixin: "USER_ACCESS.VIEW",
            StudyRoleCreateView: "USER_ACCESS.MANAGE",
            SubjectEventInstanceFileImportView: "subject.update_subject",
            SubjectAddRepeatingEventInstanceView: "subject.update_subject",
        }

        for view_class, permission_required in expected_permissions.items():
            self.assertEqual(view_class.permission_required, permission_required)

    def test_form_instance_create_requires_crf_entry_permission(self):
        request = type("Request", (), {"method": "POST"})()
        view = DataCaptureFormInstanceListCreateAPIView()

        def fake_dispatch(self, request, *args, **kwargs):
            return self.permission_required

        original_dispatch = DataCaptureFormInstanceListCreateAPIView.__mro__[1].dispatch
        try:
            DataCaptureFormInstanceListCreateAPIView.__mro__[1].dispatch = fake_dispatch
            self.assertEqual(view.dispatch(request), "CRF.ENTER")
        finally:
            DataCaptureFormInstanceListCreateAPIView.__mro__[1].dispatch = original_dispatch

    def test_role_import_post_requires_user_access_manage_permission(self):
        request = type("Request", (), {"method": "POST"})()
        view = StudyManageRolesView()

        def fake_dispatch(self, request, *args, **kwargs):
            return self.permission_required

        original_dispatch = StudyRolesContextMixin.dispatch
        try:
            StudyRolesContextMixin.dispatch = fake_dispatch
            self.assertEqual(view.dispatch(request), "USER_ACCESS.MANAGE")
        finally:
            StudyRolesContextMixin.dispatch = original_dispatch

    def test_crf_template_import_post_requires_manage_crf_template_permission(self):
        request = type("Request", (), {"method": "POST"})()
        view = StudyCrfTemplateListView()

        def fake_dispatch_authenticated(self, request):
            return self.permission_required

        original_dispatch_authenticated = StudyCrfTemplateListView.dispatch_authenticated
        try:
            StudyCrfTemplateListView.dispatch_authenticated = fake_dispatch_authenticated
            self.assertEqual(view.dispatch(request, study_id=1), "study.manage_crf_template")
        finally:
            StudyCrfTemplateListView.dispatch_authenticated = original_dispatch_authenticated

    def test_route_permissions_are_registered_for_seed(self):
        permission_codes = {
            definition.permission_code
            for definition in ALL_PERMISSION_DEFINITIONS
        }
        permission_codes.update(
            f"{definition.app_label}.{definition.codename}"
            for definition in ALL_PERMISSION_DEFINITIONS
        )
        missing_permissions = []

        for _, pattern in _flatten_url_patterns(get_resolver().url_patterns):
            for permission_code in _permission_list(_route_permission(pattern)):
                if permission_code not in permission_codes:
                    missing_permissions.append(permission_code)

        self.assertEqual(missing_permissions, [])

    def test_routes_without_business_permission_are_explicitly_allowlisted(self):
        routes_without_permissions = set()

        for route, pattern in _flatten_url_patterns(get_resolver().url_patterns):
            view_class = _route_view_class(pattern)
            module_name = getattr(view_class, "__module__", getattr(pattern.callback, "__module__", ""))
            if not (
                module_name.startswith("apps.")
                or module_name.startswith("Vanguardian")
            ):
                continue
            if not _permission_list(_route_permission(pattern)):
                routes_without_permissions.add(route)

        self.assertEqual(
            routes_without_permissions,
            EXPECTED_ROUTES_WITHOUT_BUSINESS_PERMISSION,
        )
