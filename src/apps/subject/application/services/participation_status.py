from apps.core.choices import SubjectLifecycleStatusChoices


class SubjectParticipationDisplayStatus:
    SCREEN_FAILURE = "screen_failure"
    WAITING_FOR_RANDOMIZATION_SLOT = "waiting_for_randomization_slot"
    PENDING_RANDOMIZATION = "pending_randomization"
    PENDING_ENROLLMENT = "pending_enrollment"


class SubjectParticipationStatusService:
    SCREEN_FAILURE_ENROLLMENT_STATUS = "screenfailure"
    ELIGIBLE_ENROLLMENT_STATUS = "eligible"
    RANDOMIZED_STATUSES = frozenset({"assigned", "randomized"})
    ACTIVE_SCHEME_STATUS = "active"

    @classmethod
    def resolve(
        cls,
        *,
        lifecycle_status: str,
        enrollment_status: str = "",
        is_enrolled: bool = False,
        randomization_status: str = "",
        has_randomization_slot: bool = False,
        randomization_scheme_status: str = "",
        available_randomization_slot_count=None,
    ) -> str:
        if lifecycle_status != SubjectLifecycleStatusChoices.ACTIVE:
            return lifecycle_status

        normalized_enrollment_status = cls._normalized(enrollment_status)
        if normalized_enrollment_status == cls.SCREEN_FAILURE_ENROLLMENT_STATUS:
            return SubjectParticipationDisplayStatus.SCREEN_FAILURE

        if is_enrolled:
            return lifecycle_status

        if (
            has_randomization_slot
            or cls._normalized(randomization_status) in cls.RANDOMIZED_STATUSES
        ):
            return SubjectParticipationDisplayStatus.PENDING_ENROLLMENT

        if normalized_enrollment_status != cls.ELIGIBLE_ENROLLMENT_STATUS:
            return lifecycle_status

        if cls._normalized(randomization_scheme_status) != cls.ACTIVE_SCHEME_STATUS:
            return SubjectParticipationDisplayStatus.PENDING_ENROLLMENT

        available_slot_count = cls._integer_or_none(
            available_randomization_slot_count
        )
        if available_slot_count is not None and available_slot_count <= 0:
            return SubjectParticipationDisplayStatus.WAITING_FOR_RANDOMIZATION_SLOT
        return SubjectParticipationDisplayStatus.PENDING_RANDOMIZATION

    @staticmethod
    def _normalized(value) -> str:
        return str(value or "").strip().lower()

    @staticmethod
    def _integer_or_none(value) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None


__all__ = [
    "SubjectParticipationDisplayStatus",
    "SubjectParticipationStatusService",
]
