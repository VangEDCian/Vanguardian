from importlib import import_module

__all__ = [
    "AddRepeatingSubjectEventInstanceService",
    "CreateSubjectService",
    "SubjectEventCompletionService",
    "SubjectEventInstanceResyncResult",
    "SubjectEventInstanceResyncService",
    "SubjectEventTransitionService",
    "SubjectWorkflowActionService",
    "RandomizeSubject",
    "RandomizeSubjectCommand",
    "CorrectSubjectMilestone",
    "CorrectSubjectMilestoneCommand",
]

_MODULE_BY_NAME = {
    "AddRepeatingSubjectEventInstanceService": "apps.subject.application.services.add_repeating_event_instance",
    "CreateSubjectService": "apps.subject.application.services.create_subject",
    "SubjectEventCompletionService": "apps.subject.application.services.event_completion",
    "SubjectEventInstanceResyncResult": "apps.subject.application.services.event_instance_resync",
    "SubjectEventInstanceResyncService": "apps.subject.application.services.event_instance_resync",
    "SubjectEventTransitionService": "apps.subject.application.services.event_lifecycle",
    "SubjectWorkflowActionService": "apps.subject.application.services.workflow_action",
    "RandomizeSubject": "apps.subject.application.services.randomize_subject",
    "RandomizeSubjectCommand": "apps.subject.application.services.randomize_subject",
    "CorrectSubjectMilestone": "apps.subject.application.services.subject_milestone",
    "CorrectSubjectMilestoneCommand": "apps.subject.application.services.subject_milestone",
}


def __getattr__(name):
    module_name = _MODULE_BY_NAME.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
