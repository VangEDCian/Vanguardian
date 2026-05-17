import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase

from apps.study.presentation.web.views.site import SiteMembershipOptionsApiView


class SiteMembershipOptionsApiViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _build_request(self, path):
        request = self.factory.get(path)
        request.user = SimpleNamespace(is_authenticated=True, is_superuser=True)
        return request

    @patch.object(SiteMembershipOptionsApiView, "get_command_repository")
    def test_returns_select2_results_from_study_or_site_memberships(self, mock_get_repository):
        repository = MagicMock()
        repository.list_users_for_study_or_site_membership.return_value = [
            SimpleNamespace(pk=11, first_name="Jane", last_name="Doe", display_name="", username="jane.doe"),
            SimpleNamespace(pk=12, first_name="", last_name="", display_name="John Display", username="john"),
        ]
        mock_get_repository.return_value = repository

        request = self._build_request("/api/studies/3/sites/7/memberships?q=j")
        response = SiteMembershipOptionsApiView.as_view()(request, study_id=3, site_id=7)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(
            payload,
            {
                "results": [
                    {"id": "11", "text": "Jane Doe (jane.doe)"},
                    {"id": "12", "text": "John Display (john)"},
                ],
            },
        )
        repository.list_users_for_study_or_site_membership.assert_called_once_with(
            study_id=3,
            site_id=7,
            search_query="j",
        )
