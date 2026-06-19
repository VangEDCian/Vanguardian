from apps.study.application.commands import (
    EnrollSubjectCommand,
    FinalizeEligibilityAssessmentCommand,
    MarkEligibilityStaleOnSourceDataChangeCommand,
    RecordEventGateEvaluationCommand,
    RetractEligibilityAssessmentCommand,
)
from apps.study.application.exceptions import EligibilityEnrollmentGateError
from apps.study.application.services.event_form_display_label import (
    EventFormDisplayConfigSnapshot,
    EventFormDisplayLabelService,
    EventFormDisplayLabelValidationError,
    EventFormDisplayTemplatePreview,
)
from apps.study.application.services.randomization_workflow import (
    RandomizationSlotAssignment,
    StudyRandomizationSlotAssignmentService,
)
from apps.study.application.services.site_directory import StudySiteDirectoryQueryService


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


def study_site_belongs_to_study(*, study_id: int, study_site_id: int) -> bool:
    return StudySiteDirectoryQueryService.study_site_belongs_to_study(
        study_id=study_id,
        study_site_id=study_site_id,
    )


class EventFormDisplayConfigReader:
    def __init__(self, service=None):
        self.service = service or EventFormDisplayLabelService()

    def get_config(self, *, binding_id: int) -> EventFormDisplayConfigSnapshot | None:
        return self.service.get_config(binding_id=binding_id)

    def list_binding_choices(self, *, study_id: int):
        return self.service.list_binding_choices(study_id=study_id)


class EventFormDisplayLabelRenderer:
    def __init__(self, service=None):
        self.service = service or EventFormDisplayLabelService()

    def preview(self, **kwargs) -> EventFormDisplayTemplatePreview:
        return self.service.preview(**kwargs)

    def render_label(self, **kwargs) -> str:
        return self.service.render_label(**kwargs)

    def save_config(self, **kwargs) -> EventFormDisplayConfigSnapshot:
        return self.service.save_config(**kwargs)


class StudyEventFormBindingReader:
    def __init__(self, service=None):
        self.service = service or EventFormDisplayLabelService()

    def get_binding_snapshot(self, *, binding_id: int):
        return self.service.get_binding_snapshot(binding_id=binding_id)


__all__ = [
    "RandomizationSlotAssignment",
    "EnrollSubjectCommand",
    "EligibilityEnrollmentGateError",
    "FinalizeEligibilityAssessmentCommand",
    "MarkEligibilityStaleOnSourceDataChangeCommand",
    "RecordEventGateEvaluationCommand",
    "RetractEligibilityAssessmentCommand",
    "EventFormDisplayConfigReader",
    "EventFormDisplayConfigSnapshot",
    "EventFormDisplayLabelRenderer",
    "EventFormDisplayLabelValidationError",
    "EventFormDisplayTemplatePreview",
    "StudyEventFormBindingReader",
    "assign_randomization_slot_for_subject",
    "enroll_subject_after_eligibility_gate",
    "finalize_subject_eligibility_assessment",
    "mark_subject_eligibility_stale_on_source_data_change",
    "record_event_gate_evaluation",
    "get_current_subject_treatment",
    "get_subject_treatment_timeline",
    "randomize_subject",
    "retract_subject_eligibility_assessment",
    "study_site_belongs_to_study",
]
