from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.study.application.commands.delete_randomization import (
    DeleteRandomizationArmCommand,
    DeleteRandomizationSchemeCommand,
    RandomizationDeleteBlockedError,
)
from apps.study.application.commands.delete_study import DeleteStudyCommand
from apps.study.application.commands.site_data import DeleteSiteCommand, SiteNotFoundError
from apps.study.application.queries.study_directory import StudyNotFoundError
from apps.study.application.services import (
    DeleteRandomizationArmService,
    DeleteRandomizationSchemeService,
    DeleteSiteService,
    DeleteStudyService,
)


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
    @patch("apps.study.application.services.delete_study.build_soft_deleted_unique_value")
    def test_marks_study_deleted_and_suffixes_code(self, mock_suffix_builder):
        study = _make_study(pk=1, code="STUDY-001")
        mock_suffix_builder.return_value = "STUDY-001_deleted_deadbeef"
        repository = MagicMock()
        sonic_adapter = MagicMock()
        repository.get_study.return_value = study
        repository.save_study.side_effect = lambda item: item

        result = DeleteStudyService.execute.__wrapped__(
            DeleteStudyService(repository=repository, sonic_adapter=sonic_adapter),
            DeleteStudyCommand(study_id=1, actor_user_id=42),
        )

        self.assertEqual(result.code, "STUDY-001_deleted_deadbeef")
        self.assertTrue(result.deleted)
        self.assertFalse(result.is_active)
        mock_suffix_builder.assert_called_once_with("STUDY-001")
        repository.touch_study.assert_called_once_with(study, actor_user_id=42)
        repository.save_study.assert_called_once_with(study)
        sonic_adapter.remove_study.assert_called_once_with(study_id=1)

    def test_raises_when_study_not_found(self):
        repository = MagicMock()
        repository.get_study.return_value = None

        with self.assertRaises(StudyNotFoundError):
            DeleteStudyService.execute.__wrapped__(
                DeleteStudyService(repository=repository),
                DeleteStudyCommand(study_id=999, actor_user_id=1),
            )


class DeleteSiteServiceTests(SimpleTestCase):
    @patch("apps.study.application.services.site.build_soft_deleted_unique_value")
    def test_marks_site_deleted_and_suffixes_code(self, mock_suffix_builder):
        site = _make_site(pk=7, study_id=3, code="SITE-001")
        mock_suffix_builder.return_value = "SITE-001_deleted_deadbeef"
        repository = MagicMock()
        sonic_adapter = MagicMock()
        repository.get_site.return_value = site
        repository.save_site.side_effect = lambda item: item

        result = DeleteSiteService.execute.__wrapped__(
            DeleteSiteService(repository=repository, sonic_adapter=sonic_adapter),
            DeleteSiteCommand(site_id=7, actor_user_id=21),
        )

        self.assertEqual(result.code, "SITE-001_deleted_deadbeef")
        self.assertTrue(result.deleted)
        self.assertFalse(result.is_active)
        self.assertEqual(result.study_id, 3)
        mock_suffix_builder.assert_called_once_with("SITE-001")
        repository.touch_site.assert_called_once_with(site, actor_user_id=21)
        repository.save_site.assert_called_once_with(site)
        sonic_adapter.remove_site.assert_called_once_with(site_id=7)

    def test_raises_when_site_not_found(self):
        repository = MagicMock()
        repository.get_site.return_value = None

        with self.assertRaises(SiteNotFoundError):
            DeleteSiteService.execute.__wrapped__(
                DeleteSiteService(repository=repository),
                DeleteSiteCommand(site_id=999, actor_user_id=1),
            )


class DeleteRandomizationSchemeServiceTests(SimpleTestCase):
    def test_raises_when_scheme_has_assigned_slots(self):
        scheme = MagicMock(pk=13, code="SCH-001", deleted=False)
        repository = MagicMock()
        repository.get_scheme.return_value = scheme
        repository.scheme_has_assigned_slots.return_value = True

        service = DeleteRandomizationSchemeService(
            randomization_audit_service=MagicMock(),
            repository=repository,
        )

        with self.assertRaises(RandomizationDeleteBlockedError):
            DeleteRandomizationSchemeService.execute.__wrapped__(
                service,
                DeleteRandomizationSchemeCommand(actor_user_id=5, study_id=2, scheme_id=13),
            )

    @patch("apps.study.application.services.delete_randomization.build_soft_deleted_unique_value")
    def test_soft_deletes_scheme_and_related_entities(self, mock_suffix_builder):
        now = MagicMock()
        mock_suffix_builder.return_value = "SCH-001_deleted_deadbeef"
        scheme = MagicMock(pk=13, study_id=2, code="SCH-001", deleted=False)
        repository = MagicMock()
        repository.get_scheme.return_value = scheme
        repository.scheme_has_assigned_slots.return_value = False
        repository.now.return_value = now
        repository.soft_delete_slots_for_scheme.return_value = 7
        repository.soft_delete_arms_for_scheme.return_value = 2

        audit_service = MagicMock()
        service = DeleteRandomizationSchemeService(
            randomization_audit_service=audit_service,
            repository=repository,
        )

        result = DeleteRandomizationSchemeService.execute.__wrapped__(
            service,
            DeleteRandomizationSchemeCommand(actor_user_id=5, study_id=2, scheme_id=13),
        )

        self.assertEqual(result.deleted_slot_count, 7)
        self.assertEqual(result.deleted_arm_count, 2)
        self.assertEqual(scheme.code, "SCH-001_deleted_deadbeef")
        self.assertTrue(scheme.deleted)
        repository.save_scheme.assert_called_once_with(scheme, update_fields=["code", "deleted", "updated_at"])
        audit_service.record_scheme_deleted.assert_called_once()


class DeleteRandomizationArmServiceTests(SimpleTestCase):
    def test_raises_when_arm_has_assigned_slots(self):
        arm = MagicMock(pk=19, arm_code="ARM-A", deleted=False)
        repository = MagicMock()
        repository.get_arm.return_value = arm
        repository.arm_has_assigned_slots.return_value = True

        service = DeleteRandomizationArmService(
            randomization_audit_service=MagicMock(),
            repository=repository,
        )

        with self.assertRaises(RandomizationDeleteBlockedError):
            DeleteRandomizationArmService.execute.__wrapped__(
                service,
                DeleteRandomizationArmCommand(actor_user_id=6, study_id=2, arm_id=19),
            )

    @patch("apps.study.application.services.delete_randomization.build_soft_deleted_unique_value")
    def test_soft_deletes_arm_and_related_slots(self, mock_suffix_builder):
        now = MagicMock()
        mock_suffix_builder.return_value = "ARM-A_deleted_deadbeef"
        arm = MagicMock(pk=19, arm_code="ARM-A", deleted=False)
        repository = MagicMock()
        repository.get_arm.return_value = arm
        repository.arm_has_assigned_slots.return_value = False
        repository.now.return_value = now
        repository.soft_delete_slots_for_arm.return_value = 4

        audit_service = MagicMock()
        service = DeleteRandomizationArmService(
            randomization_audit_service=audit_service,
            repository=repository,
        )

        result = DeleteRandomizationArmService.execute.__wrapped__(
            service,
            DeleteRandomizationArmCommand(actor_user_id=6, study_id=2, arm_id=19),
        )

        self.assertEqual(result.deleted_slot_count, 4)
        self.assertEqual(arm.arm_code, "ARM-A_deleted_deadbeef")
        self.assertTrue(arm.deleted)
        self.assertFalse(arm.is_active)
        repository.save_arm.assert_called_once_with(arm, update_fields=["arm_code", "deleted", "is_active", "updated_at"])
        audit_service.record_arm_deleted.assert_called_once()
