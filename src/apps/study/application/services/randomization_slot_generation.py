from dataclasses import dataclass

from django.utils import timezone
from django.utils.translation import gettext_lazy

from apps.study.application.exceptions import RandomizationSlotGenerationError
from apps.study.domain import RandomizationScheme, RandomizationSlot
from apps.study.infrastructure.repositories import DjangoRandomizationRepository


@dataclass(frozen=True)
class RandomizationSlotCapacityCheckResult:
    """Result object for target-total capacity validation."""

    target_total: int
    assigned_count: int

    @property
    def is_valid(self):
        """True when target total is not smaller than assigned slots."""
        return self.assigned_count <= self.target_total


class StudyRandomizationSlotGenerationService:
    repository_class = DjangoRandomizationRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def check_target_total_capacity(
            self,
            *,
            scheme,
            target_total: int | None = None,
    ) -> RandomizationSlotCapacityCheckResult:
        """Check whether ``target_total`` can accommodate current assigned slots.

        If ``target_total`` is omitted, the value is read from the scheme.
        Returned target is normalized to non-negative integer.
        """
        normalized_total = int(
            target_total if target_total is not None else (scheme.target_randomized_total or 0),
        )
        assigned_count = self.repository.count_assigned_slots_for_scheme(
            scheme_id=scheme.pk,
        )
        return RandomizationSlotCapacityCheckResult(
            target_total=max(normalized_total, 0),
            assigned_count=assigned_count,
        )

    def validate_target_total_capacity(
            self, *, scheme, target_total: int | None = None,
    ):
        """Validate assigned-slot capacity and raise domain error when invalid."""
        check_result = self.check_target_total_capacity(
            scheme=scheme,
            target_total=target_total,
        )
        if check_result.is_valid:
            return check_result
        raise RandomizationSlotGenerationError(
            str(
                gettext_lazy(
                    "Target Randomized Total (%(target_total)s) cannot be smaller than assigned slots (%(assigned_count)s).",
                )
                % {
                    "target_total": check_result.target_total,
                    "assigned_count": check_result.assigned_count,
                },
            ),
        )

    def generate_slots_for_scheme_arm(self, scheme, arm):  # noqa: C901
        """Reconcile available slots to match scheme ratio and target total.

        This method is idempotent for stable inputs and may be called from
        per-arm hooks; it executes only when the passed arm code participates
        in scheme allocation ratio.

        Raises:
            RandomizationSlotGenerationError: on invalid ratio references or
                impossible totals (assigned+void greater than target).
        """
        if not RandomizationScheme.is_active(getattr(scheme, "status", None)):
            return None

        ratio_source = getattr(scheme, "allocation_ratio_json", None)
        if not isinstance(ratio_source, dict):
            return None
        ratio_map = self._normalize_ratio_map(ratio_source)
        if not ratio_map:
            return None

        # Keep compatibility with current call sites passing per-arm hooks.
        if str(getattr(arm, "arm_code", "")).strip() not in ratio_map:
            return None

        active_arms = list(self.repository.list_active_arms_for_scheme(scheme_id=scheme.pk))
        arm_by_code = {str(item.arm_code).strip(): item for item in active_arms}

        missing_codes = [arm_code for arm_code in ratio_map if arm_code not in arm_by_code]
        if missing_codes:
            raise RandomizationSlotGenerationError(
                str(
                    gettext_lazy(
                        "Allocation Ratio references inactive or missing arm(s): %(arm_codes)s.",
                    )
                    % {"arm_codes": ", ".join(missing_codes)},
                ),
            )

        target_total = int(getattr(scheme, "target_randomized_total", 0) or 0)
        target_total = max(target_total, 0)
        self.validate_target_total_capacity(
            scheme=scheme,
            target_total=target_total,
        )

        slots = list(self.repository.list_slots_for_scheme(scheme_id=scheme.pk))
        assigned_count = sum(1 for slot in slots if RandomizationSlot.is_assigned(slot.status))
        void_count = sum(1 for slot in slots if RandomizationSlot.is_void(slot.status))
        if assigned_count + void_count > target_total:
            raise RandomizationSlotGenerationError(
                str(
                    gettext_lazy(
                        "Target Randomized Total (%(target_total)s) cannot be smaller than assigned + void slots (%(locked_count)s).",
                    )
                    % {
                        "target_total": target_total,
                        "locked_count": assigned_count + void_count,
                    },
                ),
            )
        remaining_available_target = max(target_total - assigned_count, 0)

        desired_available_by_code = self._allocate_available_slots_by_ratio(
            ratio_map=ratio_map,
            total_available=remaining_available_target,
        )

        available_slots_by_code = {}
        available_slots_outside_ratio = []
        for slot in slots:
            if not RandomizationSlot.is_available(slot.status):
                continue
            arm_code = str(getattr(getattr(slot, "arm", None), "arm_code", "")).strip()
            if arm_code in desired_available_by_code:
                available_slots_by_code.setdefault(arm_code, []).append(slot)
            else:
                available_slots_outside_ratio.append(slot)

        now = timezone.now()
        slot_ids_to_release = [slot.pk for slot in available_slots_outside_ratio]
        for arm_code, desired_available in desired_available_by_code.items():
            existing_available_slots = available_slots_by_code.get(arm_code, [])
            surplus_count = len(existing_available_slots) - desired_available
            if surplus_count > 0:
                surplus_slots = existing_available_slots[-surplus_count:]
                slot_ids_to_release.extend(slot.pk for slot in surplus_slots)

        if slot_ids_to_release:
            self.repository.void_available_slots(
                slot_ids=slot_ids_to_release,
                updated_at=now,
            )

        max_sequence = self.repository.get_max_slot_sequence_no_for_scheme(
            scheme_id=scheme.pk,
        )
        slots_to_create = []
        for arm_code, desired_available in desired_available_by_code.items():
            existing_available_count = len(available_slots_by_code.get(arm_code, []))
            missing_count = desired_available - existing_available_count
            if missing_count <= 0:
                continue
            arm_instance = arm_by_code[arm_code]
            for _ in range(missing_count):
                max_sequence += 1
                slots_to_create.append(
                    self.repository.build_slot(
                        scheme_id=scheme.pk,
                        arm_id=arm_instance.pk,
                        sequence_no=max_sequence,
                        block_no=None,
                        stratum_code=None,
                        status=RandomizationSlot.AVAILABLE,
                        assigned_subject_id=None,
                        assigned_event_id=None,
                        assigned_at=None,
                        void_reason=None,
                        notes=None,
                        created_at=now,
                        updated_at=now,
                        deleted=False,
                    ),
                )

        if slots_to_create:
            self.repository.bulk_create_slots(slots_to_create)
        return None

    @staticmethod
    def _normalize_ratio_map(ratio_json):
        """Normalize ratio payload to ``{ARM_CODE: positive_int_ratio}``."""
        if not isinstance(ratio_json, dict):
            return {}

        normalized_map = {}
        for raw_arm_code, raw_ratio in ratio_json.items():
            arm_code = str(raw_arm_code or "").strip()
            if not arm_code:
                continue
            try:
                ratio = int(raw_ratio)
            except (TypeError, ValueError):
                continue
            if ratio <= 0:
                continue
            normalized_map[arm_code] = ratio
        return normalized_map

    @staticmethod
    def _allocate_available_slots_by_ratio(*, ratio_map, total_available):
        """Allocate available-slot counts by ratio, assigning remainder to last arm."""
        if total_available <= 0 or not ratio_map:
            return {arm_code: 0 for arm_code in ratio_map.keys()}

        ordered_items = list(ratio_map.items())
        ratio_total = sum(ratio for _, ratio in ordered_items)
        if ratio_total <= 0:
            return {arm_code: 0 for arm_code, _ in ordered_items}

        allocation = {}
        consumed = 0
        last_index = len(ordered_items) - 1
        for index, (arm_code, ratio) in enumerate(ordered_items):
            if index == last_index:
                allocation[arm_code] = max(total_available - consumed, 0)
                continue
            arm_available = int((total_available * ratio) / ratio_total)
            allocation[arm_code] = arm_available
            consumed += arm_available
        return allocation
