from apps.datacapture.domain import DataCapturePageEntry
from apps.datacapture.infrastructure.repositories import DjangoDataCapturePageRepository


class DataCapturePageEntryReadService:

    def __init__(self, repository=None):
        self.repository = repository or DjangoDataCapturePageRepository()

    def get_latest_page_entry(self, *, subject_id: int, visit_id: int, crf_template_id: int):
        return self.repository.get_current_entry(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
        )

    def get_latest_submitted_page_entry(
        self,
        *,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
    ):
        return self.repository.get_latest_submitted_entry(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
        )

    def get_latest_active_page_entry(self, *, subject_id: int, visit_id: int, crf_template_id: int):
        latest = self.get_latest_page_entry(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
        )
        if latest is None:
            return None
        if not DataCapturePageEntry.is_active_capture_entry(latest.status):
            return None
        return latest
