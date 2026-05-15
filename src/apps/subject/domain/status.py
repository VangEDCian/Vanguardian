def _normalized(value) -> str:
    return str(value or "").strip().lower()


class SubjectEventInstance:
    """Business status rules for the ``subject_eventinstance`` table."""

    NOT_READY = "not_ready"
    PLANNED = "planned"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    VERIFIED = "verified"
    LOCKED = "locked"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"

    TERMINAL_STATUSES = frozenset(
        {
            COMPLETED,
            VERIFIED,
            LOCKED,
            SKIPPED,
        }
    )
    OPENABLE_STATUSES = frozenset(
        {
            NOT_READY,
            PLANNED,
        }
    )

    @classmethod
    def is_terminal(cls, status) -> bool:
        return _normalized(status) in cls.TERMINAL_STATUSES

    @classmethod
    def is_openable(cls, status) -> bool:
        return _normalized(status) in cls.OPENABLE_STATUSES


__all__ = ["SubjectEventInstance"]
