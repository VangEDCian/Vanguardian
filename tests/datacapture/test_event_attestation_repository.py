from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.datacapture.infrastructure.repositories.event_attestation import (
    DjangoEventAttestationRepository,
)


class DjangoEventAttestationRepositoryTests(SimpleTestCase):
    @patch(
        "apps.datacapture.infrastructure.repositories.event_attestation."
        "DataCaptureEventAttestation.objects.filter"
    )
    def test_review_completion_is_not_invalidated_by_sdv_scope_change(self, filter_mock):
        queryset = MagicMock()
        filter_mock.return_value = queryset
        queryset.exclude.return_value = queryset
        queryset.update.return_value = 2

        updated_count = DjangoEventAttestationRepository().invalidate_active_attestations(
            event_instance_id=11,
            change_type="scope",
            actor_user_id=7,
            reason_text="Monitor SDV status changed.",
        )

        self.assertEqual(updated_count, 2)
        filter_mock.assert_called_once_with(
            event_instance_id=11,
            status="ACTIVE",
            attestation_policy__invalidate_on_scope_change=True,
        )
        queryset.exclude.assert_called_once_with(
            attestation_policy__action_kind="REVIEW_COMPLETION",
        )

    @patch(
        "apps.datacapture.infrastructure.repositories.event_attestation."
        "DataCaptureEventAttestation.objects.filter"
    )
    def test_data_change_still_uses_policy_invalidation_flag(self, filter_mock):
        queryset = MagicMock()
        filter_mock.return_value = queryset
        queryset.update.return_value = 1

        updated_count = DjangoEventAttestationRepository().invalidate_active_attestations(
            event_instance_id=11,
            change_type="data",
            actor_user_id=7,
            reason_text="Submitted data changed.",
        )

        self.assertEqual(updated_count, 1)
        filter_mock.assert_called_once_with(
            event_instance_id=11,
            status="ACTIVE",
            attestation_policy__invalidate_on_data_change=True,
        )
        queryset.exclude.assert_not_called()
