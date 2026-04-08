# import datetime
# from unittest.mock import MagicMock, patch
#
# from django.test import SimpleTestCase
#
# from apps.study.application.commands.site import CreateSiteService, DeleteSiteService, UpdateSiteService
# from apps.study.application.commands.site_data import (
#     CreateSiteCommand,
#     DeleteSiteCommand,
#     SiteCodeAlreadyExistsError as SiteCommandCodeAlreadyExistsError,
#     SiteNotFoundError as SiteCommandNotFoundError,
#     UpdateSiteCommand,
# )
# from apps.study.application.commands.create_study import CreateStudyCommand, CreateStudyService
# from apps.study.application.commands.delete_study import DeleteStudyCommand, DeleteStudyService
# from apps.study.application.commands.exceptions import StudyCodeAlreadyExistsError, StudyDateRangeError
# from apps.study.application.commands.toggle_study_status import ToggleStudyStatusCommand, ToggleStudyStatusService
# from apps.study.application.commands.update_study import UpdateStudyCommand, UpdateStudyService
# from apps.study.application.queries.study_directory import StudyNotFoundError
#
#
# def _make_study(**kwargs):
#     """Return a mock Study object with sensible defaults."""
#     defaults = {
#         "pk": 1,
#         "code": "STUDY-001",
#         "name": "Test Study",
#         "sponsor": "Acme Pharma",
#         "description": "",
#         "start_date": datetime.date(2026, 1, 1),
#         "end_date": datetime.date(2026, 12, 31),
#         "is_active": True,
#         "deleted": False,
#     }
#     defaults.update(kwargs)
#     study = MagicMock(**defaults)
#     study.pk = defaults["pk"]
#     study.code = defaults["code"]
#     study.name = defaults["name"]
#     study.sponsor = defaults["sponsor"]
#     study.description = defaults["description"]
#     study.start_date = defaults["start_date"]
#     study.end_date = defaults["end_date"]
#     study.is_active = defaults["is_active"]
#     study.deleted = defaults["deleted"]
#     return study
#
#
# def _make_site(**kwargs):
#     defaults = {
#         "pk": 1,
#         "code": "SITE-001",
#         "name": "City Medical Center",
#         "investigator": "Dr. Jane Doe",
#         "study_id": 10,
#         "is_active": True,
#         "deleted": False,
#     }
#     defaults.update(kwargs)
#     site = MagicMock(**defaults)
#     site.pk = defaults["pk"]
#     site.code = defaults["code"]
#     site.name = defaults["name"]
#     site.investigator = defaults["investigator"]
#     site.study_id = defaults["study_id"]
#     site.is_active = defaults["is_active"]
#     site.deleted = defaults["deleted"]
#     return site
#
#
# class CreateStudyServiceTests(SimpleTestCase):
#
#     def _make_command(self, **overrides):
#         defaults = dict(
#             code="STUDY-001",
#             name="Test Study",
#             sponsor="Acme",
#             description="",
#             start_date=datetime.date(2026, 6, 1),
#             end_date=datetime.date(2026, 12, 31),
#             is_active=True,
#             actor_user_id=1,
#         )
#         defaults.update(overrides)
#         return CreateStudyCommand(**defaults)
#
#     @patch("apps.study.application.commands.create_study.Study")
#     def test_creates_study_successfully(self, mock_study_cls):
#         mock_study_cls.objects.filter.return_value.exists.return_value = False
#         mock_study_cls.objects.create.return_value = _make_study()
#
#         service = CreateStudyService()
#         result = service.execute(self._make_command())
#
#         mock_study_cls.objects.create.assert_called_once()
#         self.assertIsNotNone(result)
#
#     @patch("apps.study.application.commands.create_study.Study")
#     def test_raises_when_code_already_exists(self, mock_study_cls):
#         mock_study_cls.objects.filter.return_value.exists.return_value = True
#
#         service = CreateStudyService()
#         with self.assertRaises(StudyCodeAlreadyExistsError):
#             service.execute(self._make_command(code="EXISTING"))
#
#     @patch("apps.study.application.commands.create_study.Study")
#     def test_raises_when_end_date_before_start_date(self, mock_study_cls):
#         mock_study_cls.objects.filter.return_value.exists.return_value = False
#
#         service = CreateStudyService()
#         with self.assertRaises(StudyDateRangeError):
#             service.execute(
#                 self._make_command(
#                     start_date=datetime.date(2026, 12, 1),
#                     end_date=datetime.date(2026, 6, 1),
#                 )
#             )
#
#     @patch("apps.study.application.commands.create_study.Study")
#     def test_allows_no_dates(self, mock_study_cls):
#         mock_study_cls.objects.filter.return_value.exists.return_value = False
#         mock_study_cls.objects.create.return_value = _make_study(start_date=None, end_date=None)
#
#         service = CreateStudyService()
#         result = service.execute(self._make_command(start_date=None, end_date=None))
#         self.assertIsNotNone(result)
#
#
# class UpdateStudyServiceTests(SimpleTestCase):
#
#     def _make_command(self, **overrides):
#         defaults = dict(
#             study_id=1,
#             code="STUDY-001",
#             name="Updated Study",
#             sponsor="Acme",
#             description="",
#             start_date=datetime.date(2026, 6, 1),
#             end_date=datetime.date(2026, 12, 31),
#             is_active=True,
#             actor_user_id=1,
#         )
#         defaults.update(overrides)
#         return UpdateStudyCommand(**defaults)
#
#     @patch("apps.study.application.commands.update_study.Study")
#     def test_updates_study_successfully(self, mock_study_cls):
#         existing = _make_study(pk=1, code="STUDY-001")
#         mock_study_cls.objects.filter.return_value.first.return_value = existing
#         mock_study_cls.objects.filter.return_value.exclude.return_value.exists.return_value = False
#
#         service = UpdateStudyService()
#         result = service.execute(self._make_command())
#
#         existing.save.assert_called_once()
#         self.assertEqual(result, existing)
#
#     @patch("apps.study.application.commands.update_study.Study")
#     def test_raises_when_study_not_found(self, mock_study_cls):
#         mock_study_cls.objects.filter.return_value.first.return_value = None
#
#         service = UpdateStudyService()
#         with self.assertRaises(StudyNotFoundError):
#             service.execute(self._make_command(study_id=999))
#
#     @patch("apps.study.application.commands.update_study.Study")
#     def test_raises_when_code_taken_by_another_study(self, mock_study_cls):
#         existing = _make_study(pk=1)
#         mock_study_cls.objects.filter.return_value.first.return_value = existing
#         mock_study_cls.objects.filter.return_value.exclude.return_value.exists.return_value = True
#
#         service = UpdateStudyService()
#         with self.assertRaises(StudyCodeAlreadyExistsError):
#             service.execute(self._make_command(code="TAKEN"))
#
#     @patch("apps.study.application.commands.update_study.Study")
#     def test_allows_same_code_for_same_study(self, mock_study_cls):
#         """Updating a study with its own existing code must not raise."""
#         existing = _make_study(pk=1, code="STUDY-001")
#         mock_study_cls.objects.filter.return_value.first.return_value = existing
#         mock_study_cls.objects.filter.return_value.exclude.return_value.exists.return_value = False
#
#         service = UpdateStudyService()
#         result = service.execute(self._make_command(code="STUDY-001"))
#         existing.save.assert_called_once()
#         self.assertEqual(result, existing)
#
#     @patch("apps.study.application.commands.update_study.Study")
#     def test_raises_when_end_date_before_start_date(self, mock_study_cls):
#         existing = _make_study(pk=1)
#         mock_study_cls.objects.filter.return_value.first.return_value = existing
#         mock_study_cls.objects.filter.return_value.exclude.return_value.exists.return_value = False
#
#         service = UpdateStudyService()
#         with self.assertRaises(StudyDateRangeError):
#             service.execute(
#                 self._make_command(
#                     start_date=datetime.date(2026, 12, 1),
#                     end_date=datetime.date(2026, 6, 1),
#                 )
#             )
#
#
# class ToggleStudyStatusServiceTests(SimpleTestCase):
#
#     def _make_command(self, study_id=1, actor_user_id=1):
#         return ToggleStudyStatusCommand(study_id=study_id, actor_user_id=actor_user_id)
#
#     @patch("apps.study.application.commands.toggle_study_status.Study")
#     def test_activates_inactive_study(self, mock_study_cls):
#         study = _make_study(pk=1, is_active=False)
#         mock_study_cls.objects.filter.return_value.first.return_value = study
#
#         service = ToggleStudyStatusService()
#         result = service.execute(self._make_command())
#
#         self.assertTrue(result.is_active)
#         study.save.assert_called_once()
#
#     @patch("apps.study.application.commands.toggle_study_status.Study")
#     def test_deactivates_active_study(self, mock_study_cls):
#         study = _make_study(pk=1, is_active=True)
#         mock_study_cls.objects.filter.return_value.first.return_value = study
#
#         service = ToggleStudyStatusService()
#         result = service.execute(self._make_command())
#
#         self.assertFalse(result.is_active)
#         study.save.assert_called_once()
#
#     @patch("apps.study.application.commands.toggle_study_status.Study")
#     def test_raises_when_study_not_found(self, mock_study_cls):
#         mock_study_cls.objects.filter.return_value.first.return_value = None
#
#         service = ToggleStudyStatusService()
#         with self.assertRaises(StudyNotFoundError):
#             service.execute(self._make_command(study_id=999))
#
#     @patch("apps.study.application.commands.toggle_study_status.Study")
#     def test_updates_actor_and_timestamp(self, mock_study_cls):
#         study = _make_study(pk=1, is_active=True)
#         mock_study_cls.objects.filter.return_value.first.return_value = study
#
#         service = ToggleStudyStatusService()
#         service.execute(self._make_command(actor_user_id=42))
#
#         self.assertEqual(study.updated_by_id, 42)
#         self.assertIsNotNone(study.updated_at)
#
#
# class DeleteStudyServiceTests(SimpleTestCase):
#
#     def _make_command(self, study_id=1, actor_user_id=1):
#         return DeleteStudyCommand(study_id=study_id, actor_user_id=actor_user_id)
#
#     @patch("apps.study.application.commands.delete_study.Study")
#     def test_marks_study_deleted_and_inactive(self, mock_study_cls):
#         study = _make_study(pk=1, is_active=True, deleted=False)
#         mock_study_cls.objects.filter.return_value.first.return_value = study
#
#         result = DeleteStudyService().execute(self._make_command(actor_user_id=42))
#
#         self.assertTrue(result.deleted)
#         self.assertFalse(result.is_active)
#         self.assertEqual(result.updated_by_id, 42)
#         self.assertIsNotNone(result.updated_at)
#         study.save.assert_called_once()
#
#     @patch("apps.study.application.commands.delete_study.Study")
#     def test_raises_when_study_not_found(self, mock_study_cls):
#         mock_study_cls.objects.filter.return_value.first.return_value = None
#
#         with self.assertRaises(StudyNotFoundError):
#             DeleteStudyService().execute(self._make_command(study_id=999))
#
#
# class CreateSiteServiceTests(SimpleTestCase):
#
#     def _make_command(self, **overrides):
#         defaults = dict(
#             code="SITE-001",
#             name="City Medical Center",
#             investigator="Dr. Jane Doe",
#             study_id=10,
#             is_active=True,
#             actor_user_id=1,
#         )
#         defaults.update(overrides)
#         return CreateSiteCommand(**defaults)
#
#     @patch("apps.study.application.commands.site.Site")
#     def test_creates_site_successfully(self, mock_site_cls):
#         mock_site_cls.objects.filter.return_value.exists.return_value = False
#         mock_site_cls.objects.create.return_value = _make_site()
#
#         result = CreateSiteService().execute(self._make_command())
#
#         mock_site_cls.objects.create.assert_called_once()
#         self.assertIsNotNone(result)
#
#     @patch("apps.study.application.commands.site.Site")
#     def test_raises_when_code_already_exists_in_study(self, mock_site_cls):
#         mock_site_cls.objects.filter.return_value.exists.return_value = True
#
#         with self.assertRaises(SiteCommandCodeAlreadyExistsError):
#             CreateSiteService().execute(self._make_command(code="SITE-001"))
#
#
# class UpdateSiteServiceTests(SimpleTestCase):
#
#     def _make_command(self, **overrides):
#         defaults = dict(
#             site_id=1,
#             code="SITE-001",
#             name="Updated Site",
#             investigator="Dr. John Doe",
#             study_id=10,
#             is_active=False,
#             actor_user_id=1,
#         )
#         defaults.update(overrides)
#         return UpdateSiteCommand(**defaults)
#
#     @patch("apps.study.application.commands.site.Site")
#     def test_updates_site_successfully(self, mock_site_cls):
#         existing = _make_site(pk=1)
#         mock_site_cls.objects.filter.return_value.first.return_value = existing
#         mock_site_cls.objects.filter.return_value.exclude.return_value.exists.return_value = False
#
#         result = UpdateSiteService().execute(self._make_command())
#
#         self.assertEqual(existing.name, "Updated Site")
#         self.assertEqual(existing.investigator, "Dr. John Doe")
#         self.assertFalse(existing.is_active)
#         existing.save.assert_called_once()
#         self.assertEqual(result, existing)
#
#     @patch("apps.study.application.commands.site.Site")
#     def test_raises_when_site_not_found(self, mock_site_cls):
#         mock_site_cls.objects.filter.return_value.first.return_value = None
#
#         with self.assertRaises(SiteCommandNotFoundError):
#             UpdateSiteService().execute(self._make_command(site_id=999))
#
#     @patch("apps.study.application.commands.site.Site")
#     def test_raises_when_code_taken_by_another_site(self, mock_site_cls):
#         existing = _make_site(pk=1)
#         mock_site_cls.objects.filter.return_value.first.return_value = existing
#         mock_site_cls.objects.filter.return_value.exclude.return_value.exists.return_value = True
#
#         with self.assertRaises(SiteCommandCodeAlreadyExistsError):
#             UpdateSiteService().execute(self._make_command(code="TAKEN"))
#
#
# class DeleteSiteServiceTests(SimpleTestCase):
#
#     def _make_command(self, site_id=1, actor_user_id=1):
#         return DeleteSiteCommand(site_id=site_id, actor_user_id=actor_user_id)
#
#     @patch("apps.study.application.commands.site.Site")
#     def test_marks_site_deleted_and_inactive(self, mock_site_cls):
#         site = _make_site(pk=1, is_active=True, deleted=False)
#         mock_site_cls.objects.filter.return_value.first.return_value = site
#
#         result = DeleteSiteService().execute(self._make_command(actor_user_id=42))
#
#         self.assertTrue(result.deleted)
#         self.assertFalse(result.is_active)
#         self.assertEqual(result.updated_by_id, 42)
#         self.assertIsNotNone(result.updated_at)
#         site.save.assert_called_once()
#
#     @patch("apps.study.application.commands.site.Site")
#     def test_raises_when_site_not_found(self, mock_site_cls):
#         mock_site_cls.objects.filter.return_value.first.return_value = None
#
#         with self.assertRaises(SiteCommandNotFoundError):
#             DeleteSiteService().execute(self._make_command(site_id=999))
#
