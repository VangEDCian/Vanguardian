from apps.datacapture.domain import DataCapturePageEntry
from apps.datacapture.infrastructure.repositories import DjangoDataCapturePageRepository


class DataCapturePageEntryReadService:

    def __init__(self, repository=None):
        self.repository = repository or DjangoDataCapturePageRepository()

    def get_latest_page_entry(
        self,
        *,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
        event_form_binding_id: int | None = None,
    ):
        return self.repository.get_current_entry(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
            event_form_binding_id=event_form_binding_id,
        )

    def get_latest_submitted_page_entry(
        self,
        *,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
        event_form_binding_id: int | None = None,
    ):
        return self.repository.get_latest_submitted_entry(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
            event_form_binding_id=event_form_binding_id,
        )

    def get_page_entry(
        self,
        *,
        page_entry_id: int,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
        event_form_binding_id: int | None = None,
    ):
        return self.repository.get_page_entry_by_id(
            page_entry_id=page_entry_id,
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
            event_form_binding_id=event_form_binding_id,
        )

    def get_latest_active_page_entry(
        self,
        *,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
        event_form_binding_id: int | None = None,
    ):
        latest = self.get_latest_page_entry(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
            event_form_binding_id=event_form_binding_id,
        )
        if latest is None:
            return None
        if not DataCapturePageEntry.is_active_capture_entry(latest.status):
            return None
        return latest
