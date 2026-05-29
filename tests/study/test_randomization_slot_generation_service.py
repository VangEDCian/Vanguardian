from types import SimpleNamespace
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.core.choices.study import RandomizationSchemeStatusChoice, RandomizationSlotStatusChoice
from apps.study.application.services.randomization_slot_generation import (
    RandomizationSlotGenerationError,
    StudyRandomizationSlotGenerationService,
)


class _CountQuery:
    def __init__(self, count_value):
        self._count_value = count_value

    def count(self):
        return self._count_value


class _OrderByQuery:
    def __init__(self, rows):
        self._rows = rows

    def order_by(self, *_args):
        return self._rows


class _UpdateQuery:
    def __init__(self):
        self.update = MagicMock(return_value=0)


class StudyRandomizationSlotGenerationServiceTests(SimpleTestCase):
    def setUp(self):
        self.service = StudyRandomizationSlotGenerationService()

    def test_allocate_available_slots_assigns_remainder_to_last_arm(self):
        allocation = self.service._allocate_available_slots_by_ratio(
            ratio_map={"ARM-A": 1, "ARM-B": 1, "ARM-C": 1},
            total_available=10,
        )

        self.assertEqual(allocation["ARM-A"], 3)
        self.assertEqual(allocation["ARM-B"], 3)
        self.assertEqual(allocation["ARM-C"], 4)

    def test_validate_target_total_capacity_raises_when_assigned_exceeds_target(self):
        repository = MagicMock()
        repository.count_assigned_slots_for_scheme.return_value = 7
        self.service.repository = repository

        scheme = SimpleNamespace(pk=11, target_randomized_total=5)

        with self.assertRaises(RandomizationSlotGenerationError):
            self.service.validate_target_total_capacity(scheme=scheme)

    def test_generate_slots_returns_when_scheme_not_active(self):
        self.service.repository = MagicMock()

        scheme = SimpleNamespace(
            pk=1,
            status=RandomizationSchemeStatusChoice.DRAFT,
            allocation_ratio_json={"ARM-A": 1},
            target_randomized_total=10,
        )
        arm = SimpleNamespace(arm_code="ARM-A")

        result = self.service.generate_slots_for_scheme_arm(scheme=scheme, arm=arm)

        self.assertIsNone(result)
        self.service.repository.list_slots_for_scheme.assert_not_called()

    def test_generate_slots_reconciles_available_slots_with_ratio(self):
        # Existing: assigned=1, available=7 (A:5, B:1, C:1), void=1
        # Target total=8 => available target=7, ratio A:B=2:1 => desired A:4, B:3
        # Expect release pk5(A surplus) + pk7(C outside ratio) to VOID, create 2 slots for B.
        assigned_slot = SimpleNamespace(
            pk=101,
            status=RandomizationSlotStatusChoice.ASSIGNED,
            arm=SimpleNamespace(arm_code="ARM-A"),
            sequence_no=1,
        )
        void_slot = SimpleNamespace(
            pk=102,
            status=RandomizationSlotStatusChoice.VOID,
            arm=SimpleNamespace(arm_code="ARM-B"),
            sequence_no=2,
        )
        available_a_slots = [
            SimpleNamespace(
                pk=1 + idx,
                status=RandomizationSlotStatusChoice.AVAILABLE,
                arm=SimpleNamespace(arm_code="ARM-A"),
                sequence_no=3 + idx,
            )
            for idx in range(5)
        ]
        available_b_slot = SimpleNamespace(
            pk=6,
            status=RandomizationSlotStatusChoice.AVAILABLE,
            arm=SimpleNamespace(arm_code="ARM-B"),
            sequence_no=8,
        )
        available_other_slot = SimpleNamespace(
            pk=7,
            status=RandomizationSlotStatusChoice.AVAILABLE,
            arm=SimpleNamespace(arm_code="ARM-C"),
            sequence_no=9,
        )
        existing_slots = [
            assigned_slot,
            void_slot,
            *available_a_slots,
            available_b_slot,
            available_other_slot,
        ]

        active_arms = [
            SimpleNamespace(pk=201, arm_code="ARM-A"),
            SimpleNamespace(pk=202, arm_code="ARM-B"),
        ]
        repository = MagicMock()
        repository.count_assigned_slots_for_scheme.return_value = 1
        repository.list_active_arms_for_scheme.return_value = active_arms
        repository.list_slots_for_scheme.return_value = existing_slots
        repository.get_max_slot_sequence_no_for_scheme.return_value = 9
        repository.build_slot.side_effect = lambda **kwargs: SimpleNamespace(**kwargs)
        self.service.repository = repository

        scheme = SimpleNamespace(
            pk=55,
            status=RandomizationSchemeStatusChoice.ACTIVE,
            allocation_ratio_json={"ARM-A": 2, "ARM-B": 1},
            target_randomized_total=8,
        )
        arm = SimpleNamespace(arm_code="ARM-A")

        result = self.service.generate_slots_for_scheme_arm(scheme=scheme, arm=arm)

        self.assertIsNone(result)

        repository.void_available_slots.assert_called_once()
        self.assertCountEqual(repository.void_available_slots.call_args.kwargs["slot_ids"], [5, 7])
        self.assertIn("updated_at", repository.void_available_slots.call_args.kwargs)

        repository.bulk_create_slots.assert_called_once()
        created_slots = repository.bulk_create_slots.call_args.args[0]
        self.assertEqual(len(created_slots), 2)
        self.assertEqual({slot.scheme_id for slot in created_slots}, {55})
        self.assertEqual({slot.arm_id for slot in created_slots}, {202})
        self.assertEqual(
            {slot.status for slot in created_slots},
            {RandomizationSlotStatusChoice.AVAILABLE},
        )
        self.assertEqual([slot.sequence_no for slot in created_slots], [10, 11])

    def test_generate_slots_allocates_after_deleted_slot_sequence(self):
        active_arms = [SimpleNamespace(pk=201, arm_code="ARM-A")]
        repository = MagicMock()
        repository.count_assigned_slots_for_scheme.return_value = 0
        repository.list_active_arms_for_scheme.return_value = active_arms
        repository.list_slots_for_scheme.return_value = []
        repository.get_max_slot_sequence_no_for_scheme.return_value = 44
        repository.build_slot.side_effect = lambda **kwargs: SimpleNamespace(**kwargs)
        self.service.repository = repository

        scheme = SimpleNamespace(
            pk=55,
            status=RandomizationSchemeStatusChoice.ACTIVE,
            allocation_ratio_json={"ARM-A": 1},
            target_randomized_total=2,
        )

        self.service.generate_slots_for_scheme_arm(
            scheme=scheme,
            arm=SimpleNamespace(arm_code="ARM-A"),
        )

        created_slots = repository.bulk_create_slots.call_args.args[0]
        self.assertEqual([slot.sequence_no for slot in created_slots], [45, 46])

    def test_generate_slots_raises_when_ratio_contains_inactive_or_missing_arm(self):
        repository = MagicMock()
        repository.list_active_arms_for_scheme.return_value = [SimpleNamespace(pk=300, arm_code="ARM-A")]
        self.service.repository = repository

        scheme = SimpleNamespace(
            pk=77,
            status=RandomizationSchemeStatusChoice.ACTIVE,
            allocation_ratio_json={"ARM-A": 1, "ARM-B": 1},
            target_randomized_total=20,
        )

        with self.assertRaises(RandomizationSlotGenerationError):
            self.service.generate_slots_for_scheme_arm(
                scheme=scheme,
                arm=SimpleNamespace(arm_code="ARM-A"),
            )

    def test_generate_slots_raises_when_assigned_and_void_exceed_target_total(self):
        assigned_slot = SimpleNamespace(
            pk=401,
            status=RandomizationSlotStatusChoice.ASSIGNED,
            arm=SimpleNamespace(arm_code="ARM-A"),
            sequence_no=1,
        )
        void_slot = SimpleNamespace(
            pk=402,
            status=RandomizationSlotStatusChoice.VOID,
            arm=SimpleNamespace(arm_code="ARM-A"),
            sequence_no=2,
        )
        existing_slots = [assigned_slot, void_slot]

        repository = MagicMock()
        repository.count_assigned_slots_for_scheme.return_value = 1
        repository.list_active_arms_for_scheme.return_value = [SimpleNamespace(pk=501, arm_code="ARM-A")]
        repository.list_slots_for_scheme.return_value = existing_slots
        self.service.repository = repository

        scheme = SimpleNamespace(
            pk=88,
            status=RandomizationSchemeStatusChoice.ACTIVE,
            allocation_ratio_json={"ARM-A": 1},
            target_randomized_total=1,
        )

        with self.assertRaises(RandomizationSlotGenerationError):
            self.service.generate_slots_for_scheme_arm(
                scheme=scheme,
                arm=SimpleNamespace(arm_code="ARM-A"),
            )
