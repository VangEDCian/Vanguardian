from dataclasses import dataclass

from apps.subject.domain.status import SubjectPeriodStatus


@dataclass(frozen=True)
class SubjectPeriodTransitionDecision:
    current_status: str
    next_status: str | None = None
    reason: str = ""


class SubjectPeriodTransitionPolicy:
    def initialize_after_randomization(self, *, current_status) -> SubjectPeriodTransitionDecision | None:
        if SubjectPeriodStatus.normalize(current_status) != SubjectPeriodStatus.PLANNED:
            return None
        return SubjectPeriodTransitionDecision(
            current_status=SubjectPeriodStatus.ACTIVE,
            reason="randomization_assigned",
        )

    def complete_treatment(
        self,
        *,
        current_status,
        has_next_period: bool,
        requires_washout: bool,
    ) -> SubjectPeriodTransitionDecision | None:
        if SubjectPeriodStatus.normalize(current_status) != SubjectPeriodStatus.ACTIVE:
            return None
        if not has_next_period:
            return SubjectPeriodTransitionDecision(
                current_status=SubjectPeriodStatus.COMPLETED,
                reason="final_period_end_verified",
            )
        if requires_washout:
            return SubjectPeriodTransitionDecision(
                current_status=SubjectPeriodStatus.WASHOUT,
                reason="period_end_verified_washout_required",
            )
        return SubjectPeriodTransitionDecision(
            current_status=SubjectPeriodStatus.COMPLETED,
            next_status=SubjectPeriodStatus.ACTIVE,
            reason="period_end_verified",
        )

    def advance_after_washout(
        self,
        *,
        current_status,
        next_status,
    ) -> SubjectPeriodTransitionDecision | None:
        if SubjectPeriodStatus.normalize(current_status) != SubjectPeriodStatus.WASHOUT:
            return None
        if SubjectPeriodStatus.normalize(next_status) != SubjectPeriodStatus.PLANNED:
            return None
        return SubjectPeriodTransitionDecision(
            current_status=SubjectPeriodStatus.COMPLETED,
            next_status=SubjectPeriodStatus.ACTIVE,
            reason="washout_completed",
        )

    def override_advance_to_next_period(
        self,
        *,
        current_status,
        next_status,
    ) -> SubjectPeriodTransitionDecision | None:
        if SubjectPeriodStatus.normalize(current_status) not in {
            SubjectPeriodStatus.ACTIVE,
            SubjectPeriodStatus.WASHOUT,
        }:
            return None
        if SubjectPeriodStatus.normalize(next_status) != SubjectPeriodStatus.PLANNED:
            return None
        return SubjectPeriodTransitionDecision(
            current_status=SubjectPeriodStatus.COMPLETED,
            next_status=SubjectPeriodStatus.ACTIVE,
            reason="manual_period_transition_override",
        )

    def reopen_period_end(
        self,
        *,
        current_status,
        next_status=None,
    ) -> SubjectPeriodTransitionDecision | None:
        normalized_status = SubjectPeriodStatus.normalize(current_status)
        if normalized_status not in {
            SubjectPeriodStatus.WASHOUT,
            SubjectPeriodStatus.COMPLETED,
        }:
            return None
        if next_status is not None and SubjectPeriodStatus.normalize(next_status) == SubjectPeriodStatus.ACTIVE:
            return SubjectPeriodTransitionDecision(
                current_status=SubjectPeriodStatus.REVIEW_REQUIRED,
                reason="period_end_reopened_after_next_period_started",
            )
        return SubjectPeriodTransitionDecision(
            current_status=SubjectPeriodStatus.ACTIVE,
            reason="period_end_reopened",
        )


__all__ = [
    "SubjectPeriodTransitionDecision",
    "SubjectPeriodTransitionPolicy",
]
