import json
from typing import Any

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

    def get_page_state_id_for_scope(self, *, subject_id: int, visit_id: int, crf_template_id: int) -> int | None:
        page_state = self.repository.get_page_state_by_scope(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
        )
        if page_state is None:
            return None
        return int(page_state.id)

    def get_page_state_final_data_map(
        self,
        *,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
    ) -> dict[str, Any]:
        page_state = self.repository.get_page_state_by_scope(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
        )
        if page_state is None or not (page_state.final_data or "").strip():
            return {}
        try:
            parsed = json.loads(page_state.final_data)
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        if not isinstance(parsed, dict):
            return {}
        return {k: v for k, v in parsed.items() if k != "__form_verification__"}
