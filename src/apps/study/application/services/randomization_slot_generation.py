"""
Quy tắc tạo slot như sau:
- Scheme.status == "active"
- Scheme.allocation_ratio_json sẽ chứa key-value với `key` là mã ARM, `value` là tỉ lệ.
- Scheme.target_randomized_total sẽ chứa tổng số slot
- Tất cả Arms nằm trong allocation_ratio_json (là key) có `is_active == True`. Nếu không tồn tại arms theo code thì báo lỗi luôn.
- Khi tỉ lệ + total chia ra slot cho các arms không tròn số thì arms cuối nhận hết các phần số lẻ còn lại.
- Các slot có status == "assigned" hoặc status == "void" không được chỉnh sửa ở hàm này.
- Total sẽ bằng số lượng slot có status == assigned hoặc available.
- Các slot có status == "available" có thể được giải phóng nếu total trước đó lớn hơn khi import lại (import lại muốn giảm total từ 30 về 20 chẳng hạn, thì 10 slot có status == available sẽ cập nhật status = "void" và void_reason = "allocated slot")
- Khi import cần tính toán slot đang có để xử lý thêm slot hay xoá các slot, nếu công thức sẽ báo lỗi luôn (sai khi assigned + void lớn hơn total)
- Hàm kiểm tra total với số lượng slot assigned hiện có cần tác ra 1 hàm khác để lúc sau tôi sử dụng ở bước xử lý dữ liệu import => để hiển thị lỗi ở trường total cho người dùng biết luôn.

Ghi chú maintainability:
- Service này là nơi tập trung toàn bộ rule reconcile slot của randomization.
- ``check_target_total_capacity`` và ``validate_target_total_capacity`` là API dùng lại cho bước import validation.
- Reconcile chỉ tác động slot ``available``:
  + dư thì chuyển ``status=void`` + ``void_reason='allocated slot'``;
  + thiếu thì tạo mới với ``status=available`` và ``sequence_no`` tăng dần.
- Dữ liệu ratio đầu vào được chuẩn hoá về ``{ARM_CODE: positive_int_ratio}``.
- Nếu dữ liệu không khả thi (ví dụ ``assigned + void > target_total``) thì raise ``RandomizationSlotGenerationError`` để caller xử lý hiển thị lỗi nghiệp vụ.
"""

from dataclasses import dataclass

from django.utils import timezone
from django.utils.translation import gettext_lazy

from apps.core.choices.study import RandomizationSchemeStatusChoice, RandomizationSlotStatusChoice
from apps.study.infrastructure.persistence.models import (
    RandomizationArm, RandomizationScheme,
    RandomizationSlot,
)


@dataclass(frozen=True)
class RandomizationSlotCapacityCheckResult:
    """Result object for target-total capacity validation."""

    target_total: int
    assigned_count: int

    @property
    def is_valid(self):
        """True when target total is not smaller than assigned slots."""
        return self.assigned_count <= self.target_total


class RandomizationSlotGenerationError(Exception):
    """Raised when randomization slot generation cannot be safely performed."""


class StudyRandomizationSlotGenerationService:
    randomization_arm_model = RandomizationArm
    randomization_slot_model = RandomizationSlot

    def check_target_total_capacity(
            self,
            *,
            scheme: RandomizationScheme,
            target_total: int | None = None,
    ) -> RandomizationSlotCapacityCheckResult:
        """Check whether ``target_total`` can accommodate current assigned slots.

        If ``target_total`` is omitted, the value is read from the scheme.
        Returned target is normalized to non-negative integer.
        """
        normalized_total = int(
            target_total if target_total is not None else (scheme.target_randomized_total or 0),
        )
        assigned_count = self.randomization_slot_model.objects.filter(
            scheme_id=scheme.pk,
            deleted=False,
            status=RandomizationSlotStatusChoice.ASSIGNED,
        ).count()
        return RandomizationSlotCapacityCheckResult(
            target_total=max(normalized_total, 0),
            assigned_count=assigned_count,
        )

    def validate_target_total_capacity(
            self, *, scheme: RandomizationScheme, target_total: int | None = None,
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

    def generate_slots_for_scheme_arm(self, scheme: RandomizationScheme, arm: RandomizationArm):
        """Reconcile available slots to match scheme ratio and target total.

        This method is idempotent for stable inputs and may be called from
        per-arm hooks; it executes only when the passed arm code participates
        in scheme allocation ratio.

        Raises:
            RandomizationSlotGenerationError: on invalid ratio references or
                impossible totals (assigned+void greater than target).
        """
        if getattr(scheme, "status", None) != RandomizationSchemeStatusChoice.ACTIVE:
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

        active_arms = list(
            self.randomization_arm_model.objects.filter(
                scheme_id=scheme.pk,
                deleted=False,
                is_active=True,
            ),
        )
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

        slots = list(
            self.randomization_slot_model.objects.filter(
                scheme_id=scheme.pk,
                deleted=False,
            ).order_by("sequence_no", "id"),
        )
        assigned_count = sum(1 for slot in slots if slot.status == RandomizationSlotStatusChoice.ASSIGNED)
        void_count = sum(1 for slot in slots if slot.status == RandomizationSlotStatusChoice.VOID)
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
            if slot.status != RandomizationSlotStatusChoice.AVAILABLE:
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
            self.randomization_slot_model.objects.filter(
                pk__in=slot_ids_to_release,
                deleted=False,
                status=RandomizationSlotStatusChoice.AVAILABLE,
            ).update(
                status=RandomizationSlotStatusChoice.VOID,
                void_reason="allocated slot",
                updated_at=now,
            )

        max_sequence = max([int(getattr(slot, "sequence_no", 0) or 0) for slot in slots], default=0)
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
                    self.randomization_slot_model(
                        scheme_id=scheme.pk,
                        arm_id=arm_instance.pk,
                        sequence_no=max_sequence,
                        block_no=None,
                        stratum_code=None,
                        status=RandomizationSlotStatusChoice.AVAILABLE,
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
            self.randomization_slot_model.objects.bulk_create(slots_to_create)
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
