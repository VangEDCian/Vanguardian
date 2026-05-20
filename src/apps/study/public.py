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


__all__ = [
    "RandomizationSlotAssignment",
    "assign_randomization_slot_for_subject",
]
