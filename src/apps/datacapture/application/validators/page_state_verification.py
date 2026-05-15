from apps.datacapture.application.exceptions import (
    DataCaptureNoFieldDefinitionsError,
    DataCapturePageReopenReasonRequiredError,
    DataCapturePageReopenStateError,
    DataCapturePageReviewStartStateError,
    DataCapturePageStateNotReviewableError,
    DataCapturePageStatePersistError,
    DataCapturePageStateRequiredError,
    DataCapturePageVerifyStateError,
)
from apps.datacapture.domain.status import DataCapturePageState


class DataCapturePageStateVerificationValidator:
    """Reusable validation rules for form/page verification use cases."""

    @staticmethod
    def require_page_state(page_state):
        if page_state is None:
            raise DataCapturePageStateRequiredError()
        return page_state

    @staticmethod
    def require_reviewable_status(status) -> None:
        if not DataCapturePageState.can_start_or_continue_review(status):
            raise DataCapturePageStateNotReviewableError()

    @staticmethod
    def require_field_definitions(field_template_ids: tuple[int, ...]) -> None:
        if not field_template_ids:
            raise DataCaptureNoFieldDefinitionsError()

    @staticmethod
    def require_start_review_status(status) -> None:
        if not DataCapturePageState.can_start_review(status):
            raise DataCapturePageReviewStartStateError()

    @staticmethod
    def require_verify_status(status) -> None:
        if not DataCapturePageState.can_verify(status):
            raise DataCapturePageVerifyStateError()

    @staticmethod
    def require_reopen_status(status) -> None:
        if not DataCapturePageState.can_reopen(status):
            raise DataCapturePageReopenStateError()

    @staticmethod
    def require_reopen_reason(reason_text: str | None) -> str:
        normalized = (reason_text or "").strip()
        if not normalized:
            raise DataCapturePageReopenReasonRequiredError()
        return normalized

    @staticmethod
    def require_persisted(rows_updated: int) -> None:
        if int(rows_updated or 0) == 0:
            raise DataCapturePageStatePersistError()


__all__ = ["DataCapturePageStateVerificationValidator"]
