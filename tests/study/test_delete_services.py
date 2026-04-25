from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.study.application.commands.delete_study import DeleteStudyCommand, DeleteStudyService
from apps.study.application.commands.delete_randomization import (
    DeleteRandomizationArmCommand,
    DeleteRandomizationArmService,
    DeleteRandomizationSchemeCommand,
    DeleteRandomizationSchemeService,
    RandomizationDeleteBlockedError,
)
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


class DeleteRandomizationSchemeServiceTests(SimpleTestCase):
    @patch("apps.study.application.commands.delete_randomization.RandomizationArm")
    @patch("apps.study.application.commands.delete_randomization.RandomizationSlot")
    @patch("apps.study.application.commands.delete_randomization.RandomizationScheme")
    def test_raises_when_scheme_has_assigned_slots(self, mock_scheme_model, mock_slot_model, mock_arm_model):
        scheme = MagicMock(pk=13, code="SCH-001", deleted=False)
        mock_scheme_model.objects.filter.return_value.first.return_value = scheme
        mock_slot_model.objects.filter.return_value.exists.return_value = True

        service = DeleteRandomizationSchemeService(randomization_audit_service=MagicMock())
        service.randomization_scheme_model = mock_scheme_model
        service.randomization_slot_model = mock_slot_model
        service.randomization_arm_model = mock_arm_model

        with self.assertRaises(RandomizationDeleteBlockedError):
            DeleteRandomizationSchemeService.execute.__wrapped__(
                service,
                DeleteRandomizationSchemeCommand(actor_user_id=5, study_id=2, scheme_id=13),
            )

    @patch("apps.study.application.commands.delete_randomization.timezone")
    @patch("apps.study.application.commands.delete_randomization.build_soft_deleted_unique_value")
    @patch("apps.study.application.commands.delete_randomization.RandomizationArm")
    @patch("apps.study.application.commands.delete_randomization.RandomizationSlot")
    @patch("apps.study.application.commands.delete_randomization.RandomizationScheme")
    def test_soft_deletes_scheme_and_related_entities(self, mock_scheme_model, mock_slot_model, mock_arm_model, mock_suffix_builder, mock_timezone):
        now = MagicMock()
        mock_timezone.now.return_value = now
        mock_suffix_builder.return_value = "SCH-001_deleted_deadbeef"
        scheme = MagicMock(pk=13, study_id=2, code="SCH-001", deleted=False)
        mock_scheme_model.objects.filter.return_value.first.return_value = scheme

        assigned_qs = MagicMock()
        assigned_qs.exists.return_value = False
        delete_slot_qs = MagicMock()
        delete_slot_qs.update.return_value = 7
        mock_slot_model.objects.filter.side_effect = [assigned_qs, delete_slot_qs]

        delete_arm_qs = MagicMock()
        delete_arm_qs.update.return_value = 2
        mock_arm_model.objects.filter.return_value = delete_arm_qs

        audit_service = MagicMock()
        service = DeleteRandomizationSchemeService(randomization_audit_service=audit_service)
        service.randomization_scheme_model = mock_scheme_model
        service.randomization_slot_model = mock_slot_model
        service.randomization_arm_model = mock_arm_model

        result = DeleteRandomizationSchemeService.execute.__wrapped__(
            service,
            DeleteRandomizationSchemeCommand(actor_user_id=5, study_id=2, scheme_id=13),
        )

        self.assertEqual(result.deleted_slot_count, 7)
        self.assertEqual(result.deleted_arm_count, 2)
        self.assertEqual(scheme.code, "SCH-001_deleted_deadbeef")
        self.assertTrue(scheme.deleted)
        scheme.save.assert_called_once_with(update_fields=["code", "deleted", "updated_at"])
        audit_service.record_scheme_deleted.assert_called_once()


class DeleteRandomizationArmServiceTests(SimpleTestCase):
    @patch("apps.study.application.commands.delete_randomization.RandomizationSlot")
    @patch("apps.study.application.commands.delete_randomization.RandomizationArm")
    def test_raises_when_arm_has_assigned_slots(self, mock_arm_model, mock_slot_model):
        arm = MagicMock(pk=19, arm_code="ARM-A", deleted=False)
        mock_arm_model.objects.select_related.return_value.filter.return_value.first.return_value = arm
        mock_slot_model.objects.filter.return_value.exists.return_value = True

        service = DeleteRandomizationArmService(randomization_audit_service=MagicMock())
        service.randomization_arm_model = mock_arm_model
        service.randomization_slot_model = mock_slot_model

        with self.assertRaises(RandomizationDeleteBlockedError):
            DeleteRandomizationArmService.execute.__wrapped__(
                service,
                DeleteRandomizationArmCommand(actor_user_id=6, study_id=2, arm_id=19),
            )

    @patch("apps.study.application.commands.delete_randomization.timezone")
    @patch("apps.study.application.commands.delete_randomization.build_soft_deleted_unique_value")
    @patch("apps.study.application.commands.delete_randomization.RandomizationSlot")
    @patch("apps.study.application.commands.delete_randomization.RandomizationArm")
    def test_soft_deletes_arm_and_related_slots(self, mock_arm_model, mock_slot_model, mock_suffix_builder, mock_timezone):
        now = MagicMock()
        mock_timezone.now.return_value = now
        mock_suffix_builder.return_value = "ARM-A_deleted_deadbeef"
        arm = MagicMock(pk=19, arm_code="ARM-A", deleted=False)
        mock_arm_model.objects.select_related.return_value.filter.return_value.first.return_value = arm

        assigned_qs = MagicMock()
        assigned_qs.exists.return_value = False
        delete_slot_qs = MagicMock()
        delete_slot_qs.update.return_value = 4
        mock_slot_model.objects.filter.side_effect = [assigned_qs, delete_slot_qs]

        audit_service = MagicMock()
        service = DeleteRandomizationArmService(randomization_audit_service=audit_service)
        service.randomization_arm_model = mock_arm_model
        service.randomization_slot_model = mock_slot_model

        result = DeleteRandomizationArmService.execute.__wrapped__(
            service,
            DeleteRandomizationArmCommand(actor_user_id=6, study_id=2, arm_id=19),
        )

        self.assertEqual(result.deleted_slot_count, 4)
        self.assertEqual(arm.arm_code, "ARM-A_deleted_deadbeef")
        self.assertTrue(arm.deleted)
        self.assertFalse(arm.is_active)
        arm.save.assert_called_once_with(update_fields=["arm_code", "deleted", "is_active", "updated_at"])
        audit_service.record_arm_deleted.assert_called_once()

