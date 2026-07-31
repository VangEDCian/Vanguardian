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
    FINALIZED = "finalized"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"

    TERMINAL_STATUSES = frozenset(
        {
            VERIFIED,
            LOCKED,
            FINALIZED,
            SKIPPED,
            CANCELLED,
        }
    )
    TRANSITION_READY_STATUSES = frozenset(
        {
            COMPLETED,
            VERIFIED,
            LOCKED,
            FINALIZED,
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
    def is_transition_ready(cls, status) -> bool:
        return _normalized(status) in cls.TRANSITION_READY_STATUSES

    @classmethod
    def is_openable(cls, status) -> bool:
        return _normalized(status) in cls.OPENABLE_STATUSES


class SubjectPeriodStatus:
    """Business statuses for a randomized subject treatment period."""

    PLANNED = "planned"
    ACTIVE = "active"
    WASHOUT = "washout"
    COMPLETED = "completed"
    REVIEW_REQUIRED = "review_required"
    CANCELLED = "cancelled"

    VALUES = (
        PLANNED,
        ACTIVE,
        WASHOUT,
        COMPLETED,
        REVIEW_REQUIRED,
        CANCELLED,
    )

    @classmethod
    def normalize(cls, status) -> str:
        normalized = _normalized(status)
        return normalized if normalized in cls.VALUES else cls.PLANNED

    @classmethod
    def choices(cls) -> tuple[tuple[str, str], ...]:
        return tuple((value, value.replace("_", " ").title()) for value in cls.VALUES)


class SubjectPeriodOverrideReason:
    PAPER_CRF_DELAYED = "paper_crf_delayed"
    SOURCE_DOCUMENT_ISSUE = "source_document_issue"
    DATA_ENTRY_BACKLOG = "data_entry_backlog"
    PROTOCOL_DEVIATION = "protocol_deviation"
    OTHER = "other"

    VALUES = frozenset(
        {
            PAPER_CRF_DELAYED,
            SOURCE_DOCUMENT_ISSUE,
            DATA_ENTRY_BACKLOG,
            PROTOCOL_DEVIATION,
            OTHER,
        }
    )

    @classmethod
    def is_valid(cls, value) -> bool:
        return _normalized(value) in cls.VALUES


__all__ = [
    "SubjectEventInstance",
    "SubjectPeriodOverrideReason",
    "SubjectPeriodStatus",
]
