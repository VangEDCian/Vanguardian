from apps.datacapture.application.exceptions import (
    DataCaptureChangeReasonRequiredError,
    DataCaptureNoActiveDraftError,
)


class DataCaptureSaveSubmitValidator:
    """Reusable validation rules for save/submit page use cases."""

    @staticmethod
    def require_change_reasons_present(missing_reason_fields: list[str]) -> None:
        if missing_reason_fields:
            raise DataCaptureChangeReasonRequiredError()

    @staticmethod
    def require_active_draft(entry) -> None:
        if entry is None:
            raise DataCaptureNoActiveDraftError()


__all__ = ["DataCaptureSaveSubmitValidator"]
