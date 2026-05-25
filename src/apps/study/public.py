from apps.study.application.commands import (
    EnrollSubjectCommand,
    FinalizeEligibilityAssessmentCommand,
    MarkEligibilityStaleOnSourceDataChangeCommand,
    RecordEventGateEvaluationCommand,
    RetractEligibilityAssessmentCommand,
)
from apps.study.application.services.randomization_workflow import (
    RandomizationSlotAssignment,
    StudyRandomizationSlotAssignmentService,
)


def assign_randomization_slot_for_subject(
    *,
    study_id: int,
    subject_id: int,
    event_instance_id: int,
    actor_user_id: int | None = None,
) -> RandomizationSlotAssignment | None:
    return StudyRandomizationSlotAssignmentService().assign_random_available_slot(
        study_id=study_id,
        subject_id=subject_id,
        event_instance_id=event_instance_id,
        actor_user_id=actor_user_id,
    )


def finalize_subject_eligibility_assessment(command: FinalizeEligibilityAssessmentCommand):
    from apps.study.application.services.eligibility_assessment import EligibilityAssessmentService

    return EligibilityAssessmentService().finalize(command)


def retract_subject_eligibility_assessment(command: RetractEligibilityAssessmentCommand):
    from apps.study.application.services.eligibility_assessment import EligibilityAssessmentService

    return EligibilityAssessmentService().retract(command)


def mark_subject_eligibility_stale_on_source_data_change(command: MarkEligibilityStaleOnSourceDataChangeCommand):
    from apps.study.application.services.eligibility_assessment import EligibilityAssessmentService

    return EligibilityAssessmentService().mark_stale_on_source_data_change(command)


def enroll_subject_after_eligibility_gate(command: EnrollSubjectCommand):
    from apps.study.application.services.eligibility_assessment import EligibilityAssessmentService

    return EligibilityAssessmentService().enroll_subject(command)


def record_event_gate_evaluation(command: RecordEventGateEvaluationCommand):
    from apps.study.application.services.event_gate_evaluation import EventGateEvaluationRecorder

    return EventGateEvaluationRecorder().record(command)


__all__ = [
    "RandomizationSlotAssignment",
    "EnrollSubjectCommand",
    "FinalizeEligibilityAssessmentCommand",
    "MarkEligibilityStaleOnSourceDataChangeCommand",
    "RecordEventGateEvaluationCommand",
    "RetractEligibilityAssessmentCommand",
    "assign_randomization_slot_for_subject",
    "enroll_subject_after_eligibility_gate",
    "finalize_subject_eligibility_assessment",
    "mark_subject_eligibility_stale_on_source_data_change",
    "record_event_gate_evaluation",
    "retract_subject_eligibility_assessment",
]
