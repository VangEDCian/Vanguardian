from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import RequestFactory, SimpleTestCase

from apps.dashboard.presentation.web.views import DashboardMainView


class DashboardMainViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("apps.dashboard.presentation.web.views.SiteDropdownHandler")
    @patch("apps.dashboard.presentation.web.views.StudyDropdownHandler")
    def test_get_context_data_uses_dashboard_service_for_selected_scope(
        self,
        study_dropdown_handler,
        site_dropdown_handler,
    ):
        dashboard_service = Mock()
        dashboard_service.build.return_value = {
            "dashboard_scope_summary": {"scope_label": "All Sites", "scope_code": "Study Total"},
            "dashboard_site_filter_options": (),
            "dashboard_overview_cards": ({"label": "Subjects in Scope", "value": 12},),
            "dashboard_query_rows": (),
            "dashboard_query_total": 0,
            "dashboard_enrollment_rows": (),
            "dashboard_execution_rows": (),
            "dashboard_randomization_rows": (),
            "dashboard_priority_rows": (),
        }
        study_dropdown_handler.return_value.build.return_value = SimpleNamespace(
            selected_id=11,
            select_display_text="NNG-301",
        )
        site_dropdown_handler.return_value.get_objects.return_value.filter.return_value.exists.return_value = False
        request = self.factory.get("/dashboard/")
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_staff=False,
            is_superuser=False,
            pk=99,
            get_full_name=lambda: "",
            get_username=lambda: "dashboard-user",
            email="",
            phone_number="",
            display_name="",
        )

        view = DashboardMainView()
        view.request = request
        view.args = ()
        view.kwargs = {}
        view.get_dashboard_service = Mock(return_value=dashboard_service)

        context = view.get_context_data()

        self.assertEqual(context["dashboard_selected_study_label"], "NNG-301")
        self.assertIsNone(context["dashboard_selected_site_id"])
        self.assertEqual(context["dashboard_overview_cards"][0]["value"], 12)
        dashboard_service.build.assert_called_once_with(
            user=request.user,
            study_id=11,
            site_id=None,
        )
