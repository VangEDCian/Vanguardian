import hashlib
import json
from dataclasses import dataclass

from apps.datacapture.application.services.fact_evaluation import DataCaptureFactEvaluationService


@dataclass(frozen=True)
class DataCaptureFactSnapshot:
    page_state_id: int
    page_entry_id: int | None
    subject_id: int
    event_instance_id: int
    event_definition_id: int
    study_id: int
    study_version: str
    crf_template_id: int
    page_status: str
    facts: dict[str, object]
    source_data_version: int | None
    source_data_hash: str | None
    blocking_queries_open: bool | None = None


class DataCaptureFactSnapshotService:
    fact_evaluation_service_class = DataCaptureFactEvaluationService

    def __init__(self, repository=None, fact_mapping_evaluator=None, fact_evaluation_service=None):
        self.fact_evaluation_service = fact_evaluation_service or self.fact_evaluation_service_class(
            repository=repository,
            fact_mapping_evaluator=fact_mapping_evaluator,
        )

    def read_for_page_state(self, *, page_state_id: int) -> DataCaptureFactSnapshot:
        evaluation = self.fact_evaluation_service.evaluate_for_page_state(page_state_id=page_state_id)
        page_state = evaluation.page_state
        facts = dict(evaluation.facts)
        facts.setdefault("screening.page.status", page_state.status)

        return DataCaptureFactSnapshot(
            page_state_id=page_state.id,
            page_entry_id=page_state.current_entry_id,
            subject_id=page_state.subject_id,
            event_instance_id=page_state.visit_id,
            event_definition_id=page_state.event_definition_id,
            study_id=page_state.study_id,
            study_version=page_state.study_version,
            crf_template_id=page_state.crf_template_id,
            page_status=page_state.status,
            facts=facts,
            source_data_version=page_state.data_version,
            source_data_hash=self._hash_final_data(evaluation.source_data_for_hash),
            blocking_queries_open=None,
        )

    @staticmethod
    def _hash_final_data(final_data) -> str | None:
        if final_data in (None, ""):
            return None
        if isinstance(final_data, str):
            payload = final_data
        else:
            payload = json.dumps(final_data, ensure_ascii=True, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


__all__ = ["DataCaptureFactSnapshot", "DataCaptureFactSnapshotService"]
