from contextlib import nullcontext
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.db import DatabaseError
from django.test import SimpleTestCase

from apps.core.choices import EligibilityAssessmentStatusChoices, EligibilityResultChoices
from apps.study.application.services.randomization_workflow import (
    RandomizationSlotAssignmentError,
    StudyRandomizationSlotAssignmentService,
)


class StudyRandomizationSlotAssignmentServiceTests(SimpleTestCase):
    def test_assign_random_available_slot_retries_conflict_with_new_candidate(self):
        repository = _RandomizationRepositoryStub(
            results=[
                {
                    "assigned": False,
                    "slot_id": 1,
                    "scheme_id": 10,
                    "scheme_code": "RAND",
                    "arm_id": 101,
                    "arm_code": "A",
                    "arm_name": "Arm A",
                    "sequence_no": 1,
                },
                {
                    "assigned": True,
                    "slot_id": 2,
                    "scheme_id": 10,
                    "scheme_code": "RAND",
                    "arm_id": 102,
                    "arm_code": "B",
                    "arm_name": "Arm B",
                    "sequence_no": 2,
                },
            ]
        )

        with patch(
            "apps.study.application.services.randomization_workflow.transaction.atomic",
            return_value=nullcontext(),
        ):
            assignment = StudyRandomizationSlotAssignmentService(repository=repository).assign_random_available_slot(
                study_id=1,
                subject_id=20,
                event_instance_id=30,
                actor_user_id=99,
            )

        self.assertEqual(assignment.slot_id, 2)
        self.assertEqual(repository.excluded_slot_ids_by_call, [(), (1,)])

    def test_assign_random_available_slot_retries_database_lock_error(self):
        repository = _RandomizationRepositoryStub(
            results=[
                DatabaseError("locked"),
                {
                    "assigned": True,
                    "slot_id": 2,
                    "scheme_id": 10,
                    "scheme_code": "RAND",
                    "arm_id": 102,
                    "arm_code": "B",
                    "arm_name": "Arm B",
                    "sequence_no": 2,
                },
            ]
        )

        with patch(
            "apps.study.application.services.randomization_workflow.transaction.atomic",
            return_value=nullcontext(),
        ):
            assignment = StudyRandomizationSlotAssignmentService(repository=repository).assign_random_available_slot(
                study_id=1,
                subject_id=20,
                event_instance_id=30,
                actor_user_id=99,
            )

        self.assertEqual(assignment.slot_id, 2)
        self.assertEqual(len(repository.excluded_slot_ids_by_call), 2)

    def test_assign_random_available_slot_raises_after_retry_limit(self):
        repository = _RandomizationRepositoryStub(results=[DatabaseError("locked")] * 10)

        with (
            patch(
                "apps.study.application.services.randomization_workflow.transaction.atomic",
                return_value=nullcontext(),
            ),
            self.assertRaises(RandomizationSlotAssignmentError),
        ):
            StudyRandomizationSlotAssignmentService(repository=repository).assign_random_available_slot(
                study_id=1,
                subject_id=20,
                event_instance_id=30,
                actor_user_id=99,
            )

    def test_assign_random_available_slot_blocks_when_screening_pass_required_without_eligible_assessment(self):
        repository = _RandomizationRepositoryStub(results=[])
        repository.requires_screening_pass = True
        eligibility_repository = _EligibilityRepositoryStub(assessment=None)

        assignment = StudyRandomizationSlotAssignmentService(
            repository=repository,
            eligibility_repository=eligibility_repository,
        ).assign_random_available_slot(
            study_id=1,
            subject_id=20,
            event_instance_id=30,
            actor_user_id=99,
        )

        self.assertIsNone(assignment)
        self.assertEqual(repository.excluded_slot_ids_by_call, [])

    def test_assign_random_available_slot_allows_when_screening_pass_required_with_eligible_assessment(self):
        repository = _RandomizationRepositoryStub(
            results=[
                {
                    "assigned": True,
                    "slot_id": 2,
                    "scheme_id": 10,
                    "scheme_code": "RAND",
                    "arm_id": 102,
                    "arm_code": "B",
                    "arm_name": "Arm B",
                    "sequence_no": 2,
                },
            ]
        )
        repository.requires_screening_pass = True
        eligibility_repository = _EligibilityRepositoryStub(
            assessment=SimpleNamespace(
                is_current=True,
                assessment_status=EligibilityAssessmentStatusChoices.FINAL,
                result=EligibilityResultChoices.ELIGIBLE,
            )
        )

        with patch(
            "apps.study.application.services.randomization_workflow.transaction.atomic",
            return_value=nullcontext(),
        ):
            assignment = StudyRandomizationSlotAssignmentService(
                repository=repository,
                eligibility_repository=eligibility_repository,
            ).assign_random_available_slot(
                study_id=1,
                subject_id=20,
                event_instance_id=30,
                actor_user_id=99,
            )

        self.assertEqual(assignment.slot_id, 2)


class _RandomizationRepositoryStub:
    def __init__(self, *, results):
        self.results = list(results)
        self.excluded_slot_ids_by_call = []
        self.requires_screening_pass = False

    def now(self):
        return datetime(2026, 5, 20, 8, 0, tzinfo=timezone.utc)

    def active_scheme_requires_screening_pass(self, *, study_id):
        return self.requires_screening_pass

    def assign_random_available_slot_for_subject(self, **kwargs):
        self.excluded_slot_ids_by_call.append(kwargs["excluded_slot_ids"])
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class _EligibilityRepositoryStub:
    def __init__(self, *, assessment):
        self.assessment = assessment

    def get_current_assessment(self, *, study_id, subject_id, assessment_type):
        return self.assessment
