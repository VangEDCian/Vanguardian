def _normalized(value) -> str:
    return str(value or "").strip().lower()


class DataCapturePageState:
    """Business status rules for the ``datacapture_pagestate`` table."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    CORRECTION_REQUIRED = "correction_required"
    LOCKED = "locked"
    FINALIZED = "finalized"

    CAPTURE_LOCKED_STATUSES = frozenset(
        {
            VERIFIED,
            LOCKED,
            FINALIZED,
        }
    )
    EVENT_TRANSITION_STABLE_STATUSES = CAPTURE_LOCKED_STATUSES
    REVIEWABLE_STATUSES = frozenset(
        {
            SUBMITTED,
            UNDER_REVIEW,
            CORRECTION_REQUIRED,
        }
    )

    @classmethod
    def is_capture_locked(cls, status) -> bool:
        return _normalized(status) in cls.CAPTURE_LOCKED_STATUSES

    @classmethod
    def is_event_transition_stable(cls, status) -> bool:
        return _normalized(status) in cls.EVENT_TRANSITION_STABLE_STATUSES

    @classmethod
    def can_start_or_continue_review(cls, status) -> bool:
        return _normalized(status) in cls.REVIEWABLE_STATUSES

    @classmethod
    def can_start_review(cls, status) -> bool:
        return _normalized(status) in {cls.SUBMITTED, cls.CORRECTION_REQUIRED}

    @classmethod
    def is_under_review(cls, status) -> bool:
        return _normalized(status) == cls.UNDER_REVIEW

    @classmethod
    def can_verify(cls, status) -> bool:
        return cls.can_start_or_continue_review(status)

    @classmethod
    def can_reopen(cls, status) -> bool:
        return _normalized(status) == cls.VERIFIED

    @classmethod
    def requires_change_reason_on_submit(cls, status) -> bool:
        return _normalized(status) == cls.VERIFIED

    @classmethod
    def should_open_for_data_entry(cls, status) -> bool:
        return _normalized(status) == cls.NOT_STARTED

    @classmethod
    def is_correction_required(cls, status) -> bool:
        return _normalized(status) == cls.CORRECTION_REQUIRED

    @classmethod
    def is_finalized(cls, status) -> bool:
        return _normalized(status) == cls.FINALIZED


class DataCapturePageEntry:
    """Business status rules for the ``datacapture_pageentry`` table."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    SUPERSEDED = "superseded"
    CANCELLED = "cancelled"

    LATEST_ENTRY_EXCLUDED_STATUSES = frozenset(
        {
            CANCELLED,
            "canceled",
        }
    )
    ACTIVE_CAPTURE_STATUSES = frozenset(
        {
            DRAFT,
            SUBMITTED,
        }
    )

    @classmethod
    def is_draft(cls, status) -> bool:
        return _normalized(status) == cls.DRAFT

    @classmethod
    def is_submitted(cls, status) -> bool:
        return _normalized(status) == cls.SUBMITTED

    @classmethod
    def is_excluded_from_latest(cls, status) -> bool:
        return _normalized(status) in cls.LATEST_ENTRY_EXCLUDED_STATUSES

    @classmethod
    def is_active_capture_entry(cls, status) -> bool:
        return _normalized(status) in cls.ACTIVE_CAPTURE_STATUSES


class DataCaptureFieldReview:
    """Business status rules for the ``datacapture_fieldreview`` table."""

    NOT_REVIEWED = "not_reviewed"
    VERIFIED = "verified"
    WAIVED = "waived"
    STALE = "stale"

    PAGE_VERIFY_READY_STATUSES = frozenset(
        {
            VERIFIED,
            WAIVED,
        }
    )

    @classmethod
    def is_verified(cls, status) -> bool:
        return _normalized(status) == cls.VERIFIED

    @classmethod
    def is_stale(cls, status) -> bool:
        return _normalized(status) == cls.STALE

    @classmethod
    def is_ready_for_page_verify(cls, status) -> bool:
        return _normalized(status) in cls.PAGE_VERIFY_READY_STATUSES


__all__ = [
    "DataCaptureFieldReview",
    "DataCapturePageEntry",
    "DataCapturePageState",
]
