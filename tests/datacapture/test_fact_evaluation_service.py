from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.datacapture.application.commands import DataCapturePageStateNotFoundError
from apps.datacapture.application.services.fact_evaluation import DataCaptureFactEvaluationService
from apps.datacapture.application.services.fact_snapshot import DataCaptureFactSnapshotService
from apps.datacapture.application.services.trigger_event_transition import DataCapturePageStateEventTransitionService
from apps.datacapture.domain import (
    DataCaptureEventFactContext,
    DataCaptureFactForm,
    DataCaptureFactSource,
)


def _page_state(status="verified"):
    return SimpleNamespace(
        id=11,
        status=status,
        final_data='{"field":"value"}',
        data_version=3,
        current_entry_id=21,
        crf_template_id=31,
        subject_id=41,
        visit_id=51,
        event_definition_id=61,
        study_id=71,
        study_version="1.0",
    )


class _FactRepository:
    def __init__(self, page_state=None):
        self.page_state = page_state
        self.mapping_calls = []
        self.event_mapping_calls = []
        self.fact_source_calls = []
        self.event_context_calls = []

    def get_page_state_for_event_transition(self, *, page_state_id):
        return self.page_state

    def list_enabled_fact_mappings(self, **kwargs):
        self.mapping_calls.append(kwargs)
        return [SimpleNamespace(id=1, fact_key="fact.a")]

    def get_fact_source_for_event_transition(self, *, page_state_id):
        self.fact_source_calls.append(page_state_id)
        return DataCaptureFactSource(
            current_form_code="FORM_A",
            forms={
                "FORM_A": DataCaptureFactForm.from_raw(
                    data={"format": "edc.form_data.v1", "groups": {}},
                    status="verified",
                    open_queries=0,
                )
            },
        )

    def get_event_fact_context_for_event_transition(self, *, event_instance_id):
        self.event_context_calls.append(event_instance_id)
        if self.page_state is None:
            return None
        return DataCaptureEventFactContext(
            event_instance_id=event_instance_id,
            study_id=self.page_state.study_id,
            study_version=self.page_state.study_version,
            event_definition_id=self.page_state.event_definition_id,
            crf_template_ids=(31, 32),
            fact_source=DataCaptureFactSource(
                forms={
                    "FORM_A": DataCaptureFactForm.from_raw(
                        data={"format": "edc.form_data.v1", "groups": {}},
                        status="verified",
                        open_queries=0,
                    )
                },
            ),
        )

    def list_enabled_fact_mappings_for_event(self, **kwargs):
        self.event_mapping_calls.append(kwargs)
        return [SimpleNamespace(id=2, fact_key="event.fact")]


class _FactEvaluator:
    def __init__(self):
        self.calls = []

    def build_facts(self, **kwargs):
        self.calls.append(kwargs)
        return {"fact.a": True}


class _FactEvaluationService:
    def __init__(self, page_state):
        self.page_state = page_state
        self.evaluate_calls = []

    def get_page_state_or_raise(self, *, page_state_id):
        return self.page_state

    def evaluate(self, *, page_state):
        self.evaluate_calls.append(page_state.id)
        return SimpleNamespace(page_state=page_state, facts={"fact.a": True})

    def evaluate_for_page_state(self, *, page_state_id):
        self.evaluate_calls.append(page_state_id)
        return SimpleNamespace(
            page_state=self.page_state,
            facts={"fact.a": True},
            source_data_for_hash={"FORM_A": {"status": "verified"}},
        )


class _SubjectLifecycleAdapter:
    def __init__(self):
        self.calls = []

    def trigger_event_transition(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(has_changes=True)


class DataCaptureFactEvaluationServiceTests(SimpleTestCase):
    def test_evaluate_for_page_state_builds_facts_from_shared_fact_source(self):
        repository = _FactRepository(page_state=_page_state())
        evaluator = _FactEvaluator()
        service = DataCaptureFactEvaluationService(repository=repository, fact_mapping_evaluator=evaluator)

        result = service.evaluate_for_page_state(page_state_id=11)

        self.assertEqual(result.page_state.id, 11)
        self.assertEqual(result.facts, {"fact.a": True})
        self.assertEqual(repository.mapping_calls[0]["study_id"], 71)
        self.assertEqual(repository.fact_source_calls, [11])
        self.assertIsInstance(evaluator.calls[0]["fact_source"], DataCaptureFactSource)

    def test_evaluate_for_event_instance_builds_facts_from_event_fact_source(self):
        repository = _FactRepository(page_state=_page_state())
        evaluator = _FactEvaluator()
        service = DataCaptureFactEvaluationService(repository=repository, fact_mapping_evaluator=evaluator)

        result = service.evaluate_for_event_instance(event_instance_id=51)

        self.assertEqual(result.event_instance_id, 51)
        self.assertEqual(result.facts, {"fact.a": True})
        self.assertEqual(repository.event_context_calls, [51])
        self.assertEqual(repository.event_mapping_calls[0]["study_id"], 71)
        self.assertEqual(repository.event_mapping_calls[0]["event_definition_id"], 61)
        self.assertEqual(repository.event_mapping_calls[0]["crf_template_ids"], (31, 32))
        self.assertIsInstance(evaluator.calls[0]["fact_source"], DataCaptureFactSource)

    def test_evaluate_for_event_instance_returns_empty_facts_when_event_has_no_page_states(self):
        service = DataCaptureFactEvaluationService(
            repository=_FactRepository(page_state=None),
            fact_mapping_evaluator=_FactEvaluator(),
        )

        result = service.evaluate_for_event_instance(event_instance_id=999)

        self.assertEqual(result.facts, {})
        self.assertIsNone(result.fact_source)

    def test_get_page_state_or_raise_raises_when_page_state_missing(self):
        service = DataCaptureFactEvaluationService(repository=_FactRepository(page_state=None), fact_mapping_evaluator=_FactEvaluator())

        with self.assertRaises(DataCapturePageStateNotFoundError):
            service.get_page_state_or_raise(page_state_id=999)

    def test_transition_service_skips_evaluation_when_page_state_is_not_stable(self):
        evaluation_service = _FactEvaluationService(page_state=_page_state(status="submitted"))
        lifecycle_adapter = _SubjectLifecycleAdapter()
        service = DataCapturePageStateEventTransitionService(
            fact_evaluation_service=evaluation_service,
            subject_event_lifecycle_adapter=lifecycle_adapter,
        )

        result = service.execute(SimpleNamespace(page_state_id=11, actor_user_id=1, trigger_source="test"))

        self.assertEqual(result.skipped_reason, "page_state_not_stable")
        self.assertEqual(evaluation_service.evaluate_calls, [])
        self.assertEqual(lifecycle_adapter.calls, [])

    def test_snapshot_service_uses_fact_evaluation_result(self):
        page_state = _page_state()
        evaluation_service = _FactEvaluationService(page_state=page_state)
        service = DataCaptureFactSnapshotService(fact_evaluation_service=evaluation_service)

        snapshot = service.read_for_page_state(page_state_id=11)

        self.assertEqual(evaluation_service.evaluate_calls, [11])
        self.assertEqual(snapshot.facts["fact.a"], True)
        self.assertEqual(snapshot.facts["screening.page.status"], "verified")
        self.assertEqual(snapshot.source_data_version, 3)
        self.assertIsNotNone(snapshot.source_data_hash)
