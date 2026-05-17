from apps.datacapture.domain.entities import PageEntryChangeStateResult
from apps.datacapture.domain.exceptions import UnsupportedEntryStatusError
from apps.datacapture.domain.status import DataCapturePageEntry


class PageEntryChangeState:
    """Pure status transition rules for ``datacapture_pageentry`` rows."""

    @classmethod
    def create_draft(cls) -> PageEntryChangeStateResult:
        return PageEntryChangeStateResult(
            from_status=None,
            to_status=DataCapturePageEntry.DRAFT,
        )

    @classmethod
    def create_submitted(cls) -> PageEntryChangeStateResult:
        return PageEntryChangeStateResult(
            from_status=None,
            to_status=DataCapturePageEntry.SUBMITTED,
        )

    @classmethod
    def submit(cls, current_status) -> PageEntryChangeStateResult:
        cls._require_status(
            current_status,
            allowed_statuses={DataCapturePageEntry.DRAFT},
            action="submit",
        )
        return cls._result(current_status, DataCapturePageEntry.SUBMITTED)

    @classmethod
    def supersede(cls, current_status) -> PageEntryChangeStateResult:
        cls._require_status(
            current_status,
            allowed_statuses={DataCapturePageEntry.SUBMITTED},
            action="supersede",
        )
        return cls._result(current_status, DataCapturePageEntry.SUPERSEDED)

    @classmethod
    def cancel(cls, current_status) -> PageEntryChangeStateResult:
        cls._require_status(
            current_status,
            allowed_statuses={DataCapturePageEntry.DRAFT},
            action="cancel",
        )
        return cls._result(current_status, DataCapturePageEntry.CANCELLED)

    @classmethod
    def _require_status(cls, current_status, *, allowed_statuses: set[str], action: str) -> None:
        normalized_status = cls._normalize_status(current_status)
        if normalized_status not in allowed_statuses:
            allowed = ", ".join(sorted(allowed_statuses))
            raise UnsupportedEntryStatusError(
                f"Cannot {action} page entry from status {normalized_status!r}; expected one of: {allowed}."
            )

    @classmethod
    def _result(cls, from_status, to_status: str) -> PageEntryChangeStateResult:
        return PageEntryChangeStateResult(
            from_status=cls._normalize_status(from_status),
            to_status=to_status,
        )

    @staticmethod
    def _normalize_status(status) -> str:
        return str(status or "").strip().lower()


__all__ = ["PageEntryChangeState"]
