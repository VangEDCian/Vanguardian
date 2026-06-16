from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.core.choices import EligibilityAssessmentStatusChoices, EligibilityResultChoices
from apps.study.application.commands import (
    EnrollSubjectCommand,
    FinalizeEligibilityAssessmentCommand,
    MarkEligibilityStaleOnSourceDataChangeCommand,
    RetractEligibilityAssessmentCommand,
)
from apps.study.application.exceptions import EligibilityEnrollmentGateError
from apps.study.application.services.eligibility_assessment import EligibilityAssessmentService


class _FakeRepository:
    def __init__(self):
        self.assessments = []
        self.failures = []
        self.gates = []
        self.gate_conditions = []
        self.permissions = {
            "finalize_subject_eligibility",
            "retract_subject_eligibility",
            "override_subject_eligibility",
        }
        self.conditions = []
        self.fixed_now = datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc)

    def now(self):
        return self.fixed_now

    def actor_has_permission(self, *, actor_id, study_id, permission_codename):
        return permission_codename in self.permissions

    def list_active_eligibility_conditions(self, *, study_id, study_version, rule_code=None):
        return self.conditions

    def supersede_current_assessments(self, *, subject_id, assessment_type, actor_id, now):
        superseded = []
        for assessment in self.assessments:
            if assessment.subject_id == subject_id and assessment.assessment_type == assessment_type and assessment.is_current:
                assessment.is_current = False
                assessment.assessment_status = EligibilityAssessmentStatusChoices.SUPERSEDED
                superseded.append(assessment)
        return superseded

    def next_assessment_no(self, *, subject_id, assessment_type):
        existing = [
            assessment.assessment_no
            for assessment in self.assessments
            if assessment.subject_id == subject_id and assessment.assessment_type == assessment_type
        ]
        return (max(existing) if existing else 0) + 1

    def create_assessment(self, **values):
        assessment = SimpleNamespace(pk=len(self.assessments) + 1, id=len(self.assessments) + 1, **values)
        self.assessments.append(assessment)
        return assessment

    def bulk_create_failures(self, *, assessment, failures, actor_id, now):
        self.failures.extend(failures)
        return failures

    def create_gate_evaluation(self, **values):
        gate = SimpleNamespace(pk=len(self.gates) + 1, id=len(self.gates) + 1, **values)
        self.gates.append(gate)
        return gate

    def bulk_create_gate_condition_results(self, *, gate_evaluation, conditions):
        self.gate_conditions.extend(conditions)
        return conditions

    def find_gate_event_definition_id(self, *, study_id, study_version, preferred_codes):
        return 30

    def get_current_assessment(self, *, study_id, subject_id, assessment_type):
        for assessment in reversed(self.assessments):
            if assessment.study_id == study_id and assessment.subject_id == subject_id and assessment.assessment_type == assessment_type and assessment.is_current:
                return assessment
        return None

    def get_assessment_for_update(self, *, study_id, subject_id, assessment_id):
        for assessment in self.assessments:
            if assessment.study_id == study_id and assessment.subject_id == subject_id and assessment.pk == assessment_id:
                return assessment
        return None

    def save_assessment(self, assessment, *, update_fields):
        return assessment

    def list_current_final_assessments_for_source(self, **kwargs):
        return [
            assessment
            for assessment in self.assessments
            if assessment.is_current and assessment.assessment_status == EligibilityAssessmentStatusChoices.FINAL
        ]


class _FakeSubjectWorkflow:
    def __init__(self):
        self.status_transitions = []
        self.randomized = False
        self.enrolled = False

    def get_subject_scope(self, *, study_id, site_id, subject_id):
        return SimpleNamespace(study_id=study_id, site_id=site_id, subject_id=subject_id)

    def get_event_scope(self, *, event_instance_id):
        return SimpleNamespace(event_instance_id=event_instance_id, event_definition_id=20, study_version="v1")

    def mark_eligible_from_assessment(self, **kwargs):
        return self._transition(kwargs["subject_id"], "Screened", "Eligible", False)

    def mark_screen_failure_from_assessment(self, **kwargs):
        return self._transition(kwargs["subject_id"], "Screened", "ScreenFailure", False)

    def mark_screened_after_retract(self, **kwargs):
        return self._transition(kwargs["subject_id"], "Eligible", "Screened", False)

    def enroll_subject(self, **kwargs):
        return self._transition(kwargs["subject_id"], "Eligible", "Enrolled", True)

    def is_subject_randomized(self, *, study_id, subject_id):
        return self.randomized

    def is_subject_enrolled(self, *, study_id, subject_id):
        return self.enrolled

    def _transition(self, subject_id, from_status, to_status, is_enrolled):
        transition = SimpleNamespace(
            subject_id=subject_id,
            from_status=from_status,
            to_status=to_status,
            is_enrolled=is_enrolled,
            status_datetime=datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
        )
        self.status_transitions.append(transition)
        return transition


class _FakeAudit:
    def __init__(self):
        self.events = []

    def record_event(self, **kwargs):
        self.events.append(kwargs)


class _FakeFactReader:
    def __init__(self, facts):
        self.facts = facts

    def read_for_page_state(self, *, page_state_id):
        return SimpleNamespace(
            page_state_id=page_state_id,
            page_entry_id=9,
            event_instance_id=4,
            source_data_version=3,
            source_data_hash="abc123",
            blocking_queries_open=False,
            facts=self.facts,
        )


class EligibilityAssessmentServiceTests(SimpleTestCase):
    def _service(self, *, facts, repository=None):
        repository = repository or _FakeRepository()
        subject_workflow = _FakeSubjectWorkflow()
        audit = _FakeAudit()
        service = EligibilityAssessmentService(
            repository=repository,
            subject_workflow_adapter=subject_workflow,
            audit_context_adapter=audit,
            fact_reader=_FakeFactReader(facts),
            transaction_context=nullcontext,
        )
        return service, repository, subject_workflow, audit

    def _finalize_command(self):
        return FinalizeEligibilityAssessmentCommand(
            study_id=1,
            site_id=2,
            subject_id=3,
            event_instance_id=4,
            assessment_type="SCREENING",
            source_context="datacapture",
            source_object_type="PAGE_STATE",
            source_object_id=8,
            source_page_state_id=8,
            study_version="v1",
            actor_id=99,
            rule_code="ELIGIBILITY_RULE_V1",
            reason_text="assessment complete",
        )

    def test_finalize_eligible_assessment_marks_subject_eligible_and_records_gate(self):
        service, repository, subject_workflow, audit = self._service(
            facts={
                "screening.inclusion.all_required_passed": True,
                "screening.exclusion.any_exclusion_present": False,
                "screening.eligibility_conclusion": "yes",
            },
        )

        result = service.finalize(self._finalize_command())

        self.assertEqual(result.result, EligibilityResultChoices.ELIGIBLE)
        self.assertEqual(repository.assessments[0].assessment_status, EligibilityAssessmentStatusChoices.FINAL)
        self.assertTrue(repository.assessments[0].is_current)
        self.assertEqual(subject_workflow.status_transitions[0].to_status, "Eligible")
        self.assertFalse(subject_workflow.status_transitions[0].is_enrolled)
        self.assertEqual(repository.gates[0].target_action, "enroll_subject")
        self.assertEqual(repository.gates[0].result, "pass")
        self.assertTrue(audit.events)

    def test_finalize_not_eligible_creates_failures_and_screen_failure_gate(self):
        service, repository, subject_workflow, audit = self._service(
            facts={
                "screening.inclusion.all_required_passed": False,
                "screening.exclusion.any_exclusion_present": True,
                "screening.eligibility_conclusion": "no",
            },
        )

        result = service.finalize(self._finalize_command())

        self.assertEqual(result.result, EligibilityResultChoices.NOT_ELIGIBLE)
        self.assertEqual(subject_workflow.status_transitions[0].to_status, "ScreenFailure")
        self.assertGreaterEqual(len(repository.failures), 1)
        self.assertEqual(repository.gates[0].result, "fail")
        self.assertTrue(audit.events)

    def test_cannot_enroll_without_current_final_eligible_assessment(self):
        service, repository, _, _ = self._service(facts={})

        with self.assertRaises(EligibilityEnrollmentGateError):
            service.enroll_subject(
                EnrollSubjectCommand(study_id=1, site_id=2, subject_id=3, actor_id=99),
            )

        self.assertEqual(repository.gates[0].result, "fail")

    def test_finalize_new_assessment_supersedes_previous_current_assessment(self):
        repository = _FakeRepository()
        service, repository, _, audit = self._service(
            facts={
                "screening.inclusion.all_required_passed": True,
                "screening.exclusion.any_exclusion_present": False,
                "screening.eligibility_conclusion": "yes",
            },
            repository=repository,
        )
        service.finalize(self._finalize_command())

        service.finalize(self._finalize_command())

        self.assertFalse(repository.assessments[0].is_current)
        self.assertEqual(repository.assessments[0].assessment_status, EligibilityAssessmentStatusChoices.SUPERSEDED)
        self.assertTrue(repository.assessments[1].is_current)
        self.assertTrue(any("superseded" in str(event["action"].value) for event in audit.events))

    def test_retract_assessment_marks_retracted_and_returns_subject_to_screened(self):
        service, repository, subject_workflow, audit = self._service(
            facts={
                "screening.inclusion.all_required_passed": True,
                "screening.exclusion.any_exclusion_present": False,
                "screening.eligibility_conclusion": "yes",
            },
        )
        assessment_id = service.finalize(self._finalize_command()).assessment_id

        result = service.retract(
            RetractEligibilityAssessmentCommand(
                study_id=1,
                subject_id=3,
                assessment_id=assessment_id,
                actor_id=99,
                reason_code="entered_in_error",
                reason_text="Entered in error.",
            ),
        )

        self.assertEqual(result.assessment_status, EligibilityAssessmentStatusChoices.RETRACTED)
        self.assertFalse(repository.assessments[0].is_current)
        self.assertEqual(subject_workflow.status_transitions[-1].to_status, "Screened")
        self.assertTrue(any("retracted" in str(event["action"].value) for event in audit.events))

    def test_source_data_change_marks_current_final_assessment_stale(self):
        service, repository, _, audit = self._service(
            facts={
                "screening.inclusion.all_required_passed": True,
                "screening.exclusion.any_exclusion_present": False,
            },
        )
        service.finalize(self._finalize_command())

        results = service.mark_stale_on_source_data_change(
            MarkEligibilityStaleOnSourceDataChangeCommand(
                source_context="datacapture",
                source_page_state_id=8,
                actor_id=99,
            ),
        )

        self.assertEqual(results[0].assessment_status, EligibilityAssessmentStatusChoices.STALE)
        self.assertEqual(repository.assessments[0].assessment_status, EligibilityAssessmentStatusChoices.STALE)
        self.assertEqual(audit.events[-1]["after_data"]["status"], "Screened")
        self.assertTrue(any("stale" in str(event["action"].value) for event in audit.events))

    def test_study_eligibility_service_uses_public_datacapture_boundary_only(self):
        source = Path("src/apps/study/application/services/eligibility_assessment.py").read_text()

        self.assertIn("apps.datacapture.public", source)
        self.assertNotIn("apps.datacapture.infrastructure", source)
        self.assertNotIn("apps.datacapture.domain", source)
