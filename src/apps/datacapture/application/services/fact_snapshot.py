import hashlib
import json
from dataclasses import dataclass

from apps.datacapture.application.services.fact_evaluation import DataCaptureFactEvaluationService
from apps.datacapture.application.services.page_state_read import DataCapturePageStateReadService


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
        return self._build_snapshot(
            page_state_id=page_state.id,
            page_entry_id=page_state.current_entry_id,
            subject_id=page_state.subject_id,
            event_instance_id=page_state.visit_id,
            event_definition_id=page_state.event_definition_id,
            study_id=page_state.study_id,
            study_version=page_state.study_version,
            crf_template_id=page_state.crf_template_id,
            page_status=page_state.status,
            facts=evaluation.facts,
            source_data_version=page_state.data_version,
            source_data_hash=self._hash_final_data(evaluation.source_data_for_hash),
            blocking_queries_open=None,
        )

    def read_for_event_instance(self, *, event_instance_id: int) -> DataCaptureFactSnapshot:
        evaluation = self.fact_evaluation_service.evaluate_for_event_instance(event_instance_id=event_instance_id)
        reference_page_state_id = DataCapturePageStateReadService().get_latest_submitted_or_stable_page_state_id_for_event_instance(
            event_instance_id=event_instance_id
        )
        if reference_page_state_id is None:
            raise ValueError(f"Page state not found for event instance {event_instance_id}.")
        page_state = self.fact_evaluation_service.get_page_state_or_raise(page_state_id=reference_page_state_id)
        return self._build_snapshot(
            page_state_id=page_state.id,
            page_entry_id=page_state.current_entry_id,
            subject_id=page_state.subject_id,
            event_instance_id=page_state.visit_id,
            event_definition_id=page_state.event_definition_id,
            study_id=page_state.study_id,
            study_version=page_state.study_version,
            crf_template_id=page_state.crf_template_id,
            page_status=page_state.status,
            facts=evaluation.facts,
            source_data_version=page_state.data_version,
            source_data_hash=self._hash_final_data(evaluation.source_data_for_hash),
            blocking_queries_open=None,
        )

    def _build_snapshot(
        self,
        *,
        page_state_id: int,
        page_entry_id: int | None,
        subject_id: int,
        event_instance_id: int,
        event_definition_id: int,
        study_id: int,
        study_version: str,
        crf_template_id: int,
        page_status: str,
        facts: dict[str, object],
        source_data_version: int | None,
        source_data_hash: str | None,
        blocking_queries_open: bool | None,
    ) -> DataCaptureFactSnapshot:
        normalized_facts = dict(facts or {})
        normalized_facts.setdefault("screening.page.status", page_status)
        return DataCaptureFactSnapshot(
            page_state_id=page_state_id,
            page_entry_id=page_entry_id,
            subject_id=subject_id,
            event_instance_id=event_instance_id,
            event_definition_id=event_definition_id,
            study_id=study_id,
            study_version=study_version,
            crf_template_id=crf_template_id,
            page_status=page_status,
            facts=normalized_facts,
            source_data_version=source_data_version,
            source_data_hash=source_data_hash,
            blocking_queries_open=blocking_queries_open,
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
