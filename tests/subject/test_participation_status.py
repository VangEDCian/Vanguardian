from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.subject.application.services.participation_status import (
    SubjectParticipationDisplayStatus,
    SubjectParticipationStatusService,
)
from apps.subject.presentation.web.mappers.participation_status import (
    get_subject_participation_status_label,
)


class SubjectParticipationStatusServiceTests(SimpleTestCase):
    def test_screen_failure_overrides_active_lifecycle(self):
        status = SubjectParticipationStatusService.resolve(
            lifecycle_status="active",
            enrollment_status="ScreenFailure",
        )

        self.assertEqual(
            status,
            SubjectParticipationDisplayStatus.SCREEN_FAILURE,
        )

    def test_eligible_subject_waits_when_active_scheme_has_no_slot(self):
        status = SubjectParticipationStatusService.resolve(
            lifecycle_status="active",
            enrollment_status="Eligible",
            randomization_scheme_status="active",
            available_randomization_slot_count=0,
        )

        self.assertEqual(
            status,
            SubjectParticipationDisplayStatus.WAITING_FOR_RANDOMIZATION_SLOT,
        )

    def test_eligible_subject_is_pending_randomization_when_slot_exists(self):
        status = SubjectParticipationStatusService.resolve(
            lifecycle_status="active",
            enrollment_status="Eligible",
            randomization_scheme_status="active",
            available_randomization_slot_count=1,
        )

        self.assertEqual(
            status,
            SubjectParticipationDisplayStatus.PENDING_RANDOMIZATION,
        )

    def test_assigned_subject_is_pending_enrollment(self):
        status = SubjectParticipationStatusService.resolve(
            lifecycle_status="active",
            enrollment_status="Eligible",
            randomization_status="assigned",
            has_randomization_slot=True,
            randomization_scheme_status="active",
            available_randomization_slot_count=0,
        )

        self.assertEqual(
            status,
            SubjectParticipationDisplayStatus.PENDING_ENROLLMENT,
        )

    def test_terminal_lifecycle_has_priority(self):
        status = SubjectParticipationStatusService.resolve(
            lifecycle_status="early_terminated",
            enrollment_status="ScreenFailure",
        )

        self.assertEqual(status, "early_terminated")

    def test_mapper_uses_database_transition_facts_for_label(self):
        record = SimpleNamespace(
            lifecycle_status="active",
            enrollment=SimpleNamespace(
                status="Eligible",
                is_enrolled=False,
                deleted=False,
            ),
            get_lifecycle_status_display=lambda: "Active",
        )

        label = get_subject_participation_status_label(
            record,
            randomization_transition_facts={
                "randomization.scheme.status": "active",
                "randomization.available_slot_count": 0,
            },
        )

        self.assertEqual(str(label), "Waiting for Randomization Slot")
