from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.study.application.commands.site_data import UpdateSiteCommand
from apps.study.application.services.site import UpdateSiteService


class UpdateSiteServiceTests(SimpleTestCase):
    def test_assigns_site_membership_for_new_investigator(self):
        repository = MagicMock()
        site = MagicMock(pk=9, study_id=3)
        repository.get_site.return_value = site
        repository.site_membership_exists.return_value = False
        repository.save_site.return_value = site

        command = UpdateSiteCommand(
            site_id=9,
            name="Updated Site",
            investigator_id=25,
            is_active=True,
            actor_user_id=100,
        )

        UpdateSiteService.execute.__wrapped__(UpdateSiteService(repository=repository), command)

        repository.create_site_membership.assert_called_once_with(
            site_id=9,
            study_id=3,
            user_id=25,
            actor_user_id=100,
        )
        self.assertEqual(site.investigator_id, 25)

    def test_skips_site_membership_create_when_investigator_already_member(self):
        repository = MagicMock()
        site = MagicMock(pk=9, study_id=3)
        repository.get_site.return_value = site
        repository.site_membership_exists.return_value = True
        repository.save_site.return_value = site

        command = UpdateSiteCommand(
            site_id=9,
            name="Updated Site",
            investigator_id=25,
            is_active=True,
            actor_user_id=100,
        )

        UpdateSiteService.execute.__wrapped__(UpdateSiteService(repository=repository), command)

        repository.create_site_membership.assert_not_called()
        self.assertEqual(site.investigator_id, 25)
