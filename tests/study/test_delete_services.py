from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.study.application.commands.delete_study import DeleteStudyCommand, DeleteStudyService
from apps.study.application.commands.site import DeleteSiteService
from apps.study.application.commands.site_data import DeleteSiteCommand, SiteNotFoundError
from apps.study.application.queries.study_directory import StudyNotFoundError


def _make_study(**kwargs):
    defaults = {
        "pk": 1,
        "code": "STUDY-001",
        "is_active": True,
        "deleted": False,
        "updated_by_id": None,
    }
    defaults.update(kwargs)
    study = MagicMock(**defaults)
    study.pk = defaults["pk"]
    study.code = defaults["code"]
    study.is_active = defaults["is_active"]
    study.deleted = defaults["deleted"]
    study.updated_by_id = defaults["updated_by_id"]
    return study


def _make_site(**kwargs):
    defaults = {
        "pk": 1,
        "study_id": 10,
        "code": "SITE-001",
        "is_active": True,
        "deleted": False,
        "updated_by_id": None,
    }
    defaults.update(kwargs)
    site = MagicMock(**defaults)
    site.pk = defaults["pk"]
    site.study_id = defaults["study_id"]
    site.code = defaults["code"]
    site.is_active = defaults["is_active"]
    site.deleted = defaults["deleted"]
    site.updated_by_id = defaults["updated_by_id"]
    return site


class DeleteStudyServiceTests(SimpleTestCase):
    @patch("apps.study.application.commands.delete_study.build_soft_deleted_unique_value")
    @patch("apps.study.application.commands.delete_study.Study")
    def test_marks_study_deleted_and_suffixes_code(self, mock_study_cls, mock_suffix_builder):
        study = _make_study(pk=1, code="STUDY-001")
        mock_study_cls.objects.filter.return_value.first.return_value = study
        mock_suffix_builder.return_value = "STUDY-001_deleted_deadbeef"

        result = DeleteStudyService.execute.__wrapped__(
            DeleteStudyService(),
            DeleteStudyCommand(study_id=1, actor_user_id=42),
        )

        self.assertEqual(result.code, "STUDY-001_deleted_deadbeef")
        self.assertTrue(result.deleted)
        self.assertFalse(result.is_active)
        self.assertEqual(result.updated_by_id, 42)
        mock_suffix_builder.assert_called_once_with("STUDY-001")
        study.save.assert_called_once()

    @patch("apps.study.application.commands.delete_study.Study")
    def test_raises_when_study_not_found(self, mock_study_cls):
        mock_study_cls.objects.filter.return_value.first.return_value = None

        with self.assertRaises(StudyNotFoundError):
            DeleteStudyService.execute.__wrapped__(
                DeleteStudyService(),
                DeleteStudyCommand(study_id=999, actor_user_id=1),
            )


class DeleteSiteServiceTests(SimpleTestCase):
    @patch("apps.study.application.commands.site.build_soft_deleted_unique_value")
    @patch("apps.study.application.commands.site.Site")
    def test_marks_site_deleted_and_suffixes_code(self, mock_site_cls, mock_suffix_builder):
        site = _make_site(pk=7, study_id=3, code="SITE-001")
        mock_site_cls.objects.filter.return_value.first.return_value = site
        mock_suffix_builder.return_value = "SITE-001_deleted_deadbeef"

        result = DeleteSiteService.execute.__wrapped__(
            DeleteSiteService(),
            DeleteSiteCommand(site_id=7, actor_user_id=21),
        )

        self.assertEqual(result.code, "SITE-001_deleted_deadbeef")
        self.assertTrue(result.deleted)
        self.assertFalse(result.is_active)
        self.assertEqual(result.updated_by_id, 21)
        self.assertEqual(result.study_id, 3)
        mock_suffix_builder.assert_called_once_with("SITE-001")
        site.save.assert_called_once()

    @patch("apps.study.application.commands.site.Site")
    def test_raises_when_site_not_found(self, mock_site_cls):
        mock_site_cls.objects.filter.return_value.first.return_value = None

        with self.assertRaises(SiteNotFoundError):
            DeleteSiteService.execute.__wrapped__(
                DeleteSiteService(),
                DeleteSiteCommand(site_id=999, actor_user_id=1),
            )
