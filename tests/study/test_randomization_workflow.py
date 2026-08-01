from contextlib import nullcontext
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.db import DatabaseError
from django.test import SimpleTestCase

from apps.core.choices import EligibilityAssessmentStatusChoices, EligibilityResultChoices
from apps.study.application.services.randomization_workflow import (
    RandomizationSlotAssignmentError,
    StudyRandomizationSlotAssignmentService,
)
from apps.study.infrastructure.repositories.randomization import (
    DjangoRandomizationRepository,
)
from apps.study.models import RandomizationSlot


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
                    "randomization_code": "R-002",
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
        self.assertEqual(assignment.randomization_code, "R-002")
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


class DjangoRandomizationRepositoryTests(SimpleTestCase):
    def test_assign_subject_randomly_orders_all_available_slot_candidates(self):
        slot = SimpleNamespace(
            pk=7,
            scheme_id=10,
            scheme=SimpleNamespace(code="CROSS_OVER_NANOKINE_EPREX4000IU"),
            arm_id=11,
            arm=SimpleNamespace(
                arm_code="SEQ_NANOKINE_EPREX4000IU",
                arm_name="NANOKINE then EPREX",
            ),
            sequence_no=19,
            randomization_code="NNG31-019",
        )
        candidate_queryset = MagicMock()
        candidate_queryset.exclude.return_value = candidate_queryset
        candidate_queryset.order_by.return_value.first.return_value = slot
        locked_queryset = MagicMock()
        locked_queryset.select_related.return_value.filter.return_value = (
            candidate_queryset
        )

        with patch.object(RandomizationSlot, "objects") as slot_manager:
            slot_manager.select_for_update.return_value = locked_queryset
            slot_manager.filter.return_value.update.return_value = 1
            result = DjangoRandomizationRepository().assign_random_available_slot_for_subject(
                study_id=3,
                subject_id=501,
                event_instance_id=601,
                actor_user_id=99,
                now=datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc),
            )

        candidate_queryset.order_by.assert_called_once_with("?")
        self.assertEqual(candidate_queryset.exclude.call_count, 6)
        for exclude_call in candidate_queryset.exclude.call_args_list:
            type_filter = exclude_call.args[0]
            self.assertEqual(type_filter.connector, "OR")
            self.assertCountEqual(
                type_filter.children,
                [
                    ("scheme__randomization_type__iexact", "blocked"),
                    ("scheme__randomization_type__iexact", "stratified_blocked"),
                ],
            )
        self.assertEqual(result["slot_id"], 7)
        self.assertEqual(result["sequence_no"], 19)


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
