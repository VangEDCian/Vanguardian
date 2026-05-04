from apps.datacapture.infrastructure.repositories import DjangoDataCapturePageRepository


class DataCapturePageStateReadService:

    def __init__(self, repository=None):
        self.repository = repository or DjangoDataCapturePageRepository()

    def get_page_state_status(self, *, subject_id: int, visit_id: int, crf_template_id: int) -> str:
        page_state = self.repository.get_page_state_by_scope(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
        )
        if page_state is None:
            return ""
        return (page_state.status or "").strip()
