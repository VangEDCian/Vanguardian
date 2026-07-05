from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import RequestFactory, SimpleTestCase

from apps.dashboard.presentation.web.views import DashboardMainView
from apps.reconcile.application.services.query_workbench import QueryWorkbenchSummaryDTO


class DashboardMainViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("apps.dashboard.presentation.web.views.SiteDropdownHandler")
    @patch("apps.dashboard.presentation.web.views.StudyDropdownHandler")
    def test_get_context_data_builds_query_summary_card(
        self,
        study_dropdown_handler,
        site_dropdown_handler,
    ):
        reader = Mock()
        reader.read.return_value = SimpleNamespace(
            summary=QueryWorkbenchSummaryDTO(
                total=8,
                open=3,
                awaiting_site_response=0,
                awaiting_review=2,
                blocking_open=1,
                resolved=1,
                closed=1,
                validation_issues_open=0,
                hard_validation_issues_open=0,
                actionable_for_current_user=0,
            )
        )
        study_dropdown_handler.return_value.build.return_value = SimpleNamespace(selected_id=11)
        site_dropdown_handler.return_value.build.return_value = SimpleNamespace(selected_id=17)
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
        view.get_query_workbench_reader = Mock(return_value=reader)

        context = view.get_context_data()

        self.assertEqual(context["query_summary_total"], 8)
        self.assertEqual(
            [str(row["label"]) for row in context["query_summary_rows"]],
            [
                "Open",
                "Waiting CRA Review",
                "Blocking",
                "Resolved",
                "Closed",
            ],
        )
        self.assertEqual([row["count"] for row in context["query_summary_rows"]], [3, 2, 1, 1, 1])
        reader.read.assert_called_once_with(
            study_id=11,
            site_id=17,
            current_user_id=99,
            can_view_internal_thread=False,
        )
