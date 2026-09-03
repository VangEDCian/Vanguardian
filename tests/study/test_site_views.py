from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase

from apps.shared.context_processors import SiteDropdownHandler, StudyDropdownHandler
from apps.study.infrastructure.persistence.models import Site
from apps.study.presentation.web.forms.site import SitesToolbarForm
from apps.study.presentation.web.views.site import SiteListView


class SiteDropdownHandlerTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _build_request(self, *, is_superuser=False):
        request = self.factory.get("/")
        request.user = SimpleNamespace(is_authenticated=True, is_superuser=is_superuser)
        request.COOKIES = {}
        return request

    @patch("apps.shared.context_processors.StudySiteMembership")
    @patch("apps.shared.context_processors.Site")
    def test_filters_sites_using_site_membership_ids_for_non_superuser(self, mock_site_cls, mock_membership_cls):
        request = self._build_request()
        base_queryset = MagicMock()
        filtered_queryset = MagicMock()
        ordered_queryset = ["site-a"]

        mock_site_cls.objects.only.return_value.filter.return_value = base_queryset
        base_queryset.filter.return_value = filtered_queryset
        filtered_queryset.order_by.return_value = ordered_queryset

        membership_queryset = mock_membership_cls.objects.filter.return_value
        membership_queryset.values_list.return_value = [11, 12]

        result = SiteDropdownHandler(request=request, study_id=7).get_objects()

        membership_queryset.values_list.assert_called_once_with("site_id", flat=True)
        base_queryset.filter.assert_called_once_with(pk__in=[11, 12])
        filtered_queryset.order_by.assert_called_once_with("id")
        self.assertIs(result, ordered_queryset)

    @patch.object(StudyDropdownHandler, "get_objects")
    def test_dropdown_build_reuses_request_scoped_result(self, get_objects):
        request = self._build_request(is_superuser=True)
        get_objects.return_value = [SimpleNamespace(id=7, name="Study A", code="STUDY-A")]

        first = StudyDropdownHandler(request=request).build()
        second = StudyDropdownHandler(request=request).build()

        self.assertIs(second, first)
        get_objects.assert_called_once_with()

    def test_site_list_uses_only_table_pagination(self):
        self.assertIsNone(SiteListView.paginate_by)
        self.assertEqual(SiteListView.table_pagination, {"per_page": 10})

    def test_site_toolbar_can_reuse_table_paginator_total(self):
        toolbar = SitesToolbarForm(queryset=Site.objects.none(), defer_total_count=True)

        self.assertNotIn("total", toolbar.form.fields)

        toolbar.bind_total_field(total_value=17)

        self.assertIn("total", toolbar.form.fields)
        self.assertEqual(toolbar.form.fields["total"].widget.total_value, 17)

    @patch("apps.shared.context_processors.StudySiteMembership")
    @patch("apps.shared.context_processors.Site")
    def test_superuser_bypasses_site_membership_filter(self, mock_site_cls, mock_membership_cls):
        request = self._build_request(is_superuser=True)
        base_queryset = MagicMock()
        ordered_queryset = ["site-a"]

        mock_site_cls.objects.only.return_value.filter.return_value = base_queryset
        base_queryset.order_by.return_value = ordered_queryset

        result = SiteDropdownHandler(request=request, study_id=7).get_objects()

        mock_membership_cls.objects.filter.assert_not_called()
        base_queryset.order_by.assert_called_once_with("id")
        self.assertIs(result, ordered_queryset)
