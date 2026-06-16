def _normalized(value) -> str:
    return str(value or "").strip().lower()


class RandomizationScheme:
    """Business status rules for the ``study_randomizationscheme`` table."""

    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"
    RETRIED = "retried"
    STATUSES = frozenset({DRAFT, ACTIVE, CLOSED, RETRIED})

    @classmethod
    def is_active(cls, status) -> bool:
        return _normalized(status) == cls.ACTIVE


class RandomizationSlot:
    """Business status rules for the ``study_randomizationslot`` table."""

    AVAILABLE = "available"
    ASSIGNED = "assigned"
    VOID = "void"
    STATUSES = frozenset({AVAILABLE, ASSIGNED, VOID})

    @classmethod
    def is_available(cls, status) -> bool:
        return _normalized(status) == cls.AVAILABLE

    @classmethod
    def is_assigned(cls, status) -> bool:
        return _normalized(status) == cls.ASSIGNED

    @classmethod
    def is_void(cls, status) -> bool:
        return _normalized(status) == cls.VOID


__all__ = [
    "RandomizationScheme",
    "RandomizationSlot",
]
