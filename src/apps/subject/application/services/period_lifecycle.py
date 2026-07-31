from dataclasses import dataclass

from django.db import transaction

from apps.subject.domain import (
    SubjectPeriodStatus,
    SubjectPeriodTransitionDecision,
    SubjectPeriodTransitionPolicy,
)
from apps.subject.infrastructure.repositories import (
    DjangoSubjectPeriodLifecycleRepository,
)


@dataclass(frozen=True)
class SubjectPeriodTransitionApplied:
    period_id: int
    period_no: int
    from_status: str
    to_status: str
    reason: str


@dataclass(frozen=True)
class SubjectPeriodLifecycleResult:
    subject_id: int
    applied_transitions: tuple[SubjectPeriodTransitionApplied, ...] = ()

    @property
    def has_changes(self) -> bool:
        return bool(self.applied_transitions)


class SubjectPeriodLifecycleService:
    repository_class = DjangoSubjectPeriodLifecycleRepository
    transition_policy_class = SubjectPeriodTransitionPolicy
    PERIOD_END_READY_STATUSES = frozenset({"verified", "locked"})
    WASHOUT_READY_STATUSES = frozenset({"completed", "verified", "locked"})

    def __init__(self, repository=None, transition_policy=None):
        self.repository = repository or self.repository_class()
        self.transition_policy = transition_policy or self.transition_policy_class()

    @transaction.atomic
    def initialize_after_randomization(
        self,
        *,
        subject_id: int,
        actor_user_id: int | None = None,
    ) -> SubjectPeriodLifecycleResult:
        periods = self.repository.list_periods_for_update(subject_id=subject_id)
        if not periods:
            return SubjectPeriodLifecycleResult(subject_id=subject_id)
        if any(
            SubjectPeriodStatus.normalize(period.status) != SubjectPeriodStatus.PLANNED
            for period in periods
        ):
            return SubjectPeriodLifecycleResult(subject_id=subject_id)

        current_period = periods[0]
        decision = self.transition_policy.initialize_after_randomization(
            current_status=current_period.status,
        )
        if decision is None:
            return SubjectPeriodLifecycleResult(subject_id=subject_id)
        return self._apply_decision(
            current_period=current_period,
            next_period=None,
            decision=decision,
            source_event_instance_id=None,
            trigger_source="subject_randomized",
            actor_user_id=actor_user_id,
            facts={"subject_id": subject_id},
            now=self.repository.now(),
        )

    @transaction.atomic
    def handle_event_status_changed(
        self,
        *,
        event_instance_id: int,
        actor_user_id: int | None = None,
        trigger_source: str = "subject_event_status_changed",
    ) -> SubjectPeriodLifecycleResult:
        event = self.repository.get_event_context(event_instance_id=event_instance_id)
        if event is None:
            return SubjectPeriodLifecycleResult(subject_id=0)
        periods = self.repository.list_periods_for_update(subject_id=event.subject_id)
        if not periods:
            return SubjectPeriodLifecycleResult(subject_id=event.subject_id)

        event_status = str(event.status or "").strip().lower()
        event_category = str(event.event_category or "").strip().lower()
        if event_category == "washout" and event_status in self.WASHOUT_READY_STATUSES:
            return self._advance_after_washout_locked(
                subject_id=event.subject_id,
                periods=periods,
                source_event_instance_id=event.event_instance_id,
                actor_user_id=actor_user_id,
                trigger_source=trigger_source,
                now=self.repository.now(),
                require_due=True,
            )

        period_index = next(
            (
                index
                for index, period in enumerate(periods)
                if period.end_event_instance_id == event.event_instance_id
            ),
            None,
        )
        if period_index is None:
            return SubjectPeriodLifecycleResult(subject_id=event.subject_id)

        current_period = periods[period_index]
        next_period = periods[period_index + 1] if period_index + 1 < len(periods) else None
        now = self.repository.now()
        if event_status in self.PERIOD_END_READY_STATUSES:
            decision = self.transition_policy.complete_treatment(
                current_status=current_period.status,
                has_next_period=next_period is not None,
                requires_washout=self._requires_washout(current_period),
            )
            if decision is None:
                return SubjectPeriodLifecycleResult(subject_id=event.subject_id)
            self.repository.record_period_end(
                period=current_period,
                source_event_instance_id=event.event_instance_id,
                occurred_at=now,
                actor_user_id=actor_user_id,
            )
            return self._apply_decision(
                current_period=current_period,
                next_period=next_period,
                decision=decision,
                source_event_instance_id=event.event_instance_id,
                trigger_source=trigger_source,
                actor_user_id=actor_user_id,
                facts={
                    "event_status": event_status,
                    "period_no": current_period.period_no,
                },
                now=now,
            )

        if event_status != "in_progress":
            return SubjectPeriodLifecycleResult(subject_id=event.subject_id)
        decision = self.transition_policy.reopen_period_end(
            current_status=current_period.status,
            next_status=getattr(next_period, "status", None),
        )
        if decision is None:
            return SubjectPeriodLifecycleResult(subject_id=event.subject_id)
        result = self._apply_decision(
            current_period=current_period,
            next_period=next_period,
            decision=decision,
            source_event_instance_id=event.event_instance_id,
            trigger_source=trigger_source,
            actor_user_id=actor_user_id,
            facts={
                "event_status": event_status,
                "period_no": current_period.period_no,
            },
            now=now,
        )
        if decision.current_status == SubjectPeriodStatus.ACTIVE:
            self.repository.correct_period_end(
                period=current_period,
                source_event_instance_id=event.event_instance_id,
                actor_user_id=actor_user_id,
                now=now,
            )
        return result

    @transaction.atomic
    def advance_after_washout(
        self,
        *,
        subject_id: int,
        actor_user_id: int | None = None,
        source_event_instance_id: int | None = None,
        trigger_source: str = "manual_period_transition",
    ) -> SubjectPeriodLifecycleResult:
        periods = self.repository.list_periods_for_update(subject_id=subject_id)
        return self._advance_after_washout_locked(
            subject_id=subject_id,
            periods=periods,
            source_event_instance_id=source_event_instance_id,
            actor_user_id=actor_user_id,
            trigger_source=trigger_source,
            now=self.repository.now(),
            require_due=True,
        )

    def process_due_transitions(
        self,
        *,
        actor_user_id: int | None = None,
        limit: int = 500,
    ) -> tuple[SubjectPeriodLifecycleResult, ...]:
        now = self.repository.now()
        subject_ids = self.repository.list_due_washout_subject_ids(
            as_of=now,
            limit=limit,
        )
        return tuple(
            self.advance_after_washout(
                subject_id=subject_id,
                actor_user_id=actor_user_id,
                trigger_source="period_transition_due",
            )
            for subject_id in subject_ids
        )

    def _advance_after_washout_locked(
        self,
        *,
        subject_id,
        periods,
        source_event_instance_id,
        actor_user_id,
        trigger_source,
        now,
        require_due,
    ) -> SubjectPeriodLifecycleResult:
        current_index = next(
            (
                index
                for index, period in enumerate(periods)
                if SubjectPeriodStatus.normalize(period.status) == SubjectPeriodStatus.WASHOUT
            ),
            None,
        )
        if current_index is None or current_index + 1 >= len(periods):
            return SubjectPeriodLifecycleResult(subject_id=subject_id)

        current_period = periods[current_index]
        next_period = periods[current_index + 1]
        if require_due and not self.repository.is_washout_due(
            period=current_period,
            as_of=now,
        ):
            return SubjectPeriodLifecycleResult(subject_id=subject_id)
        decision = self.transition_policy.advance_after_washout(
            current_status=current_period.status,
            next_status=next_period.status,
        )
        if decision is None:
            return SubjectPeriodLifecycleResult(subject_id=subject_id)
        self.repository.record_washout_end(
            period=current_period,
            source_event_instance_id=source_event_instance_id,
            occurred_at=now,
            actor_user_id=actor_user_id,
        )
        return self._apply_decision(
            current_period=current_period,
            next_period=next_period,
            decision=decision,
            source_event_instance_id=source_event_instance_id,
            trigger_source=trigger_source,
            actor_user_id=actor_user_id,
            facts={
                "period_no": current_period.period_no,
                "next_period_no": next_period.period_no,
            },
            now=now,
        )

    def _apply_decision(
        self,
        *,
        current_period,
        next_period,
        decision: SubjectPeriodTransitionDecision,
        source_event_instance_id,
        trigger_source,
        actor_user_id,
        facts,
        now,
    ) -> SubjectPeriodLifecycleResult:
        transitions = []
        updated_current = self.repository.transition_period(
            period=current_period,
            to_status=decision.current_status,
            source_event_instance_id=source_event_instance_id,
            trigger_source=trigger_source,
            reason=decision.reason,
            facts=facts,
            actor_user_id=actor_user_id,
            now=now,
        )
        if updated_current.status != current_period.status:
            transitions.append(
                self._transition_applied(
                    before=current_period,
                    after=updated_current,
                    reason=decision.reason,
                )
            )

        if next_period is not None and decision.next_status is not None:
            updated_next = self.repository.transition_period(
                period=next_period,
                to_status=decision.next_status,
                source_event_instance_id=source_event_instance_id,
                trigger_source=trigger_source,
                reason=decision.reason,
                facts=facts,
                actor_user_id=actor_user_id,
                now=now,
            )
            if updated_next.status != next_period.status:
                transitions.append(
                    self._transition_applied(
                        before=next_period,
                        after=updated_next,
                        reason=decision.reason,
                    )
                )
                if decision.next_status == SubjectPeriodStatus.ACTIVE:
                    self.repository.record_period_start(
                        period=updated_next,
                        source_event_instance_id=source_event_instance_id,
                        occurred_at=now,
                        actor_user_id=actor_user_id,
                    )

        return SubjectPeriodLifecycleResult(
            subject_id=current_period.subject_id,
            applied_transitions=tuple(transitions),
        )

    @staticmethod
    def _requires_washout(period) -> bool:
        transition_rule_code = str(period.transition_rule_code or "").strip().lower()
        return bool(period.washout_days and period.washout_days > 0) or transition_rule_code in {
            "after_washout",
            "washout",
        }

    @staticmethod
    def _transition_applied(*, before, after, reason):
        return SubjectPeriodTransitionApplied(
            period_id=before.id,
            period_no=before.period_no,
            from_status=before.status,
            to_status=after.status,
            reason=reason,
        )


__all__ = [
    "SubjectPeriodLifecycleResult",
    "SubjectPeriodLifecycleService",
    "SubjectPeriodTransitionApplied",
]
