def _normalized(value) -> str:
    return str(value or "").strip().lower()


class ReconcileDataQuery:
    """Business status rules for the ``reconcile_dataquery`` table."""

    OPEN = "open"
    ANSWERED = "answered"
    RESOLVED = "resolved"
    CLOSED = "closed"
    CANCELLED = "cancelled"

    INACTIVE_STATUSES = frozenset(
        {
            CLOSED,
            CANCELLED,
        }
    )

    @classmethod
    def inactive_statuses(cls) -> tuple[str, ...]:
        return tuple(sorted(cls.INACTIVE_STATUSES))

    @classmethod
    def is_active(cls, status) -> bool:
        return _normalized(status) not in cls.INACTIVE_STATUSES


__all__ = ["ReconcileDataQuery"]
