from datetime import date
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.study.application.commands.create_study import CreateStudyCommand
from apps.study.application.commands.site_data import CreateSiteCommand
from apps.study.application.services.create_study import CreateStudyService
from apps.study.application.services.site import CreateSiteService


class CreateStudyServiceTests(SimpleTestCase):
    def test_indexes_study_in_sonic_after_create(self):
        repository = MagicMock()
        sonic_adapter = MagicMock()
        repository.study_code_exists.return_value = False
        repository.create_study.return_value = MagicMock(
            pk=11,
            code="STUDY-011",
            name="Study 11",
            sponsor="Sponsor A",
            description="Desc",
        )

        command = CreateStudyCommand(
            code="STUDY-011",
            name="Study 11",
            sponsor="Sponsor A",
            description="Desc",
            is_active=True,
            actor_user_id=10,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        result = CreateStudyService(repository=repository, sonic_adapter=sonic_adapter).execute(command)

        self.assertEqual(result.pk, 11)
        sonic_adapter.index_study.assert_called_once_with(
            study_id=11,
            code="STUDY-011",
            name="Study 11",
            sponsor="Sponsor A",
            description="Desc",
        )


class CreateSiteServiceTests(SimpleTestCase):
    def test_indexes_site_in_sonic_after_create(self):
        repository = MagicMock()
        sonic_adapter = MagicMock()
        repository.site_code_exists.return_value = False
        repository.create_site.return_value = MagicMock(
            pk=7,
            code="SITE-007",
            name="Site 7",
            investigator="Dr. Jane",
        )
        command = CreateSiteCommand(
            code="SITE-007",
            name="Site 7",
            investigator="Dr. Jane",
            study_id=3,
            is_active=True,
            actor_user_id=99,
        )

        result = CreateSiteService.execute.__wrapped__(
            CreateSiteService(repository=repository, sonic_adapter=sonic_adapter),
            command,
        )

        self.assertEqual(result.pk, 7)
        sonic_adapter.index_site.assert_called_once_with(
            site_id=7,
            code="SITE-007",
            name="Site 7",
            investigator="Dr. Jane",
        )
