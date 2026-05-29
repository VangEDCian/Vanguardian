from apps.study.application.commands import (
    EnrollSubjectCommand,
    FinalizeEligibilityAssessmentCommand,
    MarkEligibilityStaleOnSourceDataChangeCommand,
    RecordEventGateEvaluationCommand,
    RetractEligibilityAssessmentCommand,
)
from apps.study.application.exceptions import EligibilityEnrollmentGateError
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
    scheme_id: int | None = None,
    stratum_code: str | None = None,
) -> RandomizationSlotAssignment | None:
    return StudyRandomizationSlotAssignmentService().assign_random_available_slot(
        study_id=study_id,
        subject_id=subject_id,
        event_instance_id=event_instance_id,
        actor_user_id=actor_user_id,
        scheme_id=scheme_id,
        stratum_code=stratum_code,
    )


def randomize_subject(**kwargs):
    from apps.subject.application.services.randomize_subject import RandomizeSubject, RandomizeSubjectCommand

    return RandomizeSubject().execute(RandomizeSubjectCommand(**kwargs))


def get_subject_treatment_timeline(subject_id: int):
    from apps.subject.application.services.treatment_timeline import SubjectTreatmentTimelineService

    return SubjectTreatmentTimelineService().get_subject_treatment_timeline(subject_id=subject_id)


def get_current_subject_treatment(
    subject_id: int,
    *,
    event_instance_id: int | None = None,
    as_of=None,
):
    from apps.subject.application.services.treatment_timeline import SubjectTreatmentTimelineService

    return SubjectTreatmentTimelineService().get_current_subject_treatment(
        subject_id=subject_id,
        event_instance_id=event_instance_id,
        as_of=as_of,
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
    "EligibilityEnrollmentGateError",
    "FinalizeEligibilityAssessmentCommand",
    "MarkEligibilityStaleOnSourceDataChangeCommand",
    "RecordEventGateEvaluationCommand",
    "RetractEligibilityAssessmentCommand",
    "assign_randomization_slot_for_subject",
    "enroll_subject_after_eligibility_gate",
    "finalize_subject_eligibility_assessment",
    "mark_subject_eligibility_stale_on_source_data_change",
    "record_event_gate_evaluation",
    "get_current_subject_treatment",
    "get_subject_treatment_timeline",
    "randomize_subject",
    "retract_subject_eligibility_assessment",
]
