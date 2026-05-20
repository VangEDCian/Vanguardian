from contextlib import nullcontext
from datetime import datetime, timezone
from unittest.mock import patch

from django.db import DatabaseError
from django.test import SimpleTestCase

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


class _RandomizationRepositoryStub:
    def __init__(self, *, results):
        self.results = list(results)
        self.excluded_slot_ids_by_call = []

    def now(self):
        return datetime(2026, 5, 20, 8, 0, tzinfo=timezone.utc)

    def assign_random_available_slot_for_subject(self, **kwargs):
        self.excluded_slot_ids_by_call.append(kwargs["excluded_slot_ids"])
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result
