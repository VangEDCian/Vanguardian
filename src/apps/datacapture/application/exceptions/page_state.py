from apps.datacapture.application.exceptions.base import DataCaptureValidationError


class DataCapturePageStateRequiredError(DataCaptureValidationError):
    default_message = "No page state exists for this subject visit and form."


class DataCapturePageStateNotReviewableError(DataCaptureValidationError):
    default_message = (
        "Verify can only run while the page state is submitted, under_review, or correction_required."
    )


class DataCaptureNoFieldDefinitionsError(DataCaptureValidationError):
    default_message = "No field definitions exist for this CRF template."


class DataCapturePageReviewStartStateError(DataCaptureValidationError):
    default_message = "Review can only start from a submitted or correction_required page state."


class DataCapturePageVerifyStateError(DataCaptureValidationError):
    default_message = "Page can only be verified from submitted, under_review, or correction_required state."


class DataCapturePageReopenStateError(DataCaptureValidationError):
    default_message = "Page can only be reopened from verified state."


class DataCapturePageReopenReasonRequiredError(DataCaptureValidationError):
    default_message = "Reopen reason is required."


class DataCapturePageFinalizeStateError(DataCaptureValidationError):
    default_message = "Page data can only be finalized from verified state."


class DataCapturePageLockStateError(DataCaptureValidationError):
    default_message = "Page can only be locked from finalized state."


class DataCapturePageStatePersistError(DataCaptureValidationError):
    default_message = "Could not persist verification: page state update affected 0 rows."


__all__ = [
    "DataCaptureNoFieldDefinitionsError",
    "DataCapturePageFinalizeStateError",
    "DataCapturePageLockStateError",
    "DataCapturePageReopenStateError",
    "DataCapturePageReopenReasonRequiredError",
    "DataCapturePageReviewStartStateError",
    "DataCapturePageStateNotReviewableError",
    "DataCapturePageStatePersistError",
    "DataCapturePageStateRequiredError",
    "DataCapturePageVerifyStateError",
]
