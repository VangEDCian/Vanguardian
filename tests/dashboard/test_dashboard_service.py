from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.dashboard.application.services import DashboardOverviewService


class DashboardOverviewServiceTests(SimpleTestCase):
    def test_build_returns_empty_scope_when_no_study_is_selected(self):
        service = DashboardOverviewService()

        context = service.build(
            user=SimpleNamespace(pk=99),
            study_id=None,
        )

        self.assertEqual(context["dashboard_overview_cards"][0]["value"], 0)
        self.assertEqual(context["dashboard_query_total"], 0)
        self.assertEqual(context["dashboard_execution_rows"][-1]["count"], 0)
        self.assertEqual(context["dashboard_priority_rows"][0]["tone"], "good")
        self.assertEqual(context["dashboard_site_filter_options"][0]["value"], "")
