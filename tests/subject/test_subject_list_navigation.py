from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.subject.presentation.web.tables import SubjectListTable
from apps.subject.presentation.web.views.detail import SubjectDetailView
from apps.subject.presentation.web.views.listing import SubjectListView


class SubjectListRowNavigationTests(SimpleTestCase):
    def test_crf_change_permission_has_highest_priority(self):
        self.assertEqual(
            self._resolve(
                can_change_crf_data=True,
                can_verify_form=True,
                can_view_subject=True,
            ),
            "/studies/1/subjects/11/",
        )

    def test_verify_permission_routes_to_verification_mode(self):
        self.assertEqual(
            self._resolve(
                can_change_crf_data=False,
                can_verify_form=True,
                can_view_subject=True,
            ),
            "/studies/1/subjects/11/?mode=verification",
        )

    def test_view_permission_routes_to_viewonly_mode(self):
        self.assertEqual(
            self._resolve(
                can_change_crf_data=False,
                can_verify_form=False,
                can_view_subject=True,
            ),
            "/studies/1/subjects/11/?mode=viewonly",
        )

    def test_no_permission_disables_row_navigation(self):
        self.assertEqual(
            self._resolve(
                can_change_crf_data=False,
                can_verify_form=False,
                can_view_subject=False,
            ),
            "",
        )

    def test_detail_mode_resolves_first_event_and_form(self):
        view = SubjectDetailView()
        view.object = SimpleNamespace(pk=11)
        view.get_study_id = lambda: 1
        navigation = [{"id": 262, "forms": [{"id": 1}]}]

        self.assertEqual(
            view._first_readonly_mode_url(
                mode="verification",
                event_navigation_submitted=navigation,
            ),
            "/studies/1/subjects/11/?mode=verification&event=262&form=1",
        )
        self.assertEqual(
            view._first_readonly_mode_url(
                mode="viewonly",
                event_navigation_submitted=navigation,
            ),
            "/studies/1/subjects/11/?mode=viewonly&event=262&form=1",
        )

    def test_builds_navigation_permissions_for_each_subject_site(self):
        view = SubjectListView()
        view.kwargs = {"study_id": 1}
        view.request = SimpleNamespace(user=SimpleNamespace(pk=99))

        def permission_allowed(_user, permission_code, *, site_id, **_kwargs):
            return permission_code == "SDV.MARK" and site_id == 2

        with patch(
            "apps.subject.presentation.web.views.listing.user_can_access_permission",
            side_effect=permission_allowed,
        ):
            urls = view._build_detail_url_by_subject_id(
                subject_site_by_id={11: 2, 12: 3},
            )

        self.assertEqual(
            urls,
            {
                11: "/studies/1/subjects/11/?mode=verification",
                12: "",
            },
        )

    def test_table_uses_explicit_row_url_with_separate_subject_code_column(self):
        detail_url = "/studies/1/subjects/11/?mode=viewonly"
        record = self._record()
        table = self._table(
            record=record,
            detail_url_by_subject_id={11: detail_url},
        )

        self.assertEqual(table.rows[0].attrs["data-detail-href"], detail_url)
        self.assertIn("subject_code", table.columns.names())

    def test_table_emits_empty_explicit_url_when_navigation_is_denied(self):
        record = self._record()
        table = self._table(record=record, detail_url_by_subject_id={})

        self.assertEqual(table.rows[0].attrs["data-detail-href"], "")
        common_table_source = Path(
            "src/staticfiles/shared/js/components/common-table.js"
        ).read_text()
        self.assertIn(
            'row.hasAttribute("data-detail-href")',
            common_table_source,
        )

    @staticmethod
    def _resolve(**permissions):
        return SubjectListView._resolve_detail_url(
            study_id=1,
            subject_id=11,
            **permissions,
        )

    @staticmethod
    def _record():
        return SimpleNamespace(
            pk=11,
            study_id=1,
            subject_code="SUBJ-011",
            screening_code="SCR-011",
        )

    @staticmethod
    def _table(*, record, detail_url_by_subject_id):
        return SubjectListTable(
            [record],
            verify_show_by_subject_id={},
            current_treatment_by_subject_id={},
            workflow_action_event_id_by_subject_id={},
            detail_url_by_subject_id=detail_url_by_subject_id,
            can_update_subject=False,
        )
