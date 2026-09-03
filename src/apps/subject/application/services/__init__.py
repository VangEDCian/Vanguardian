from importlib import import_module

__all__ = [
    "AddRepeatingSubjectEventInstanceService",
    "SubjectBulkActionResult",
    "SubjectBulkActionService",
    "CreateSubjectService",
    "SubjectDuePeriodTransitionResult",
    "SubjectDuePeriodTransitionService",
    "SubjectEventCompletionService",
    "SubjectEventInstanceResyncResult",
    "SubjectEventInstanceResyncService",
    "SubjectEventTransitionService",
    "SubjectPeriodLifecycleResult",
    "SubjectPeriodLifecycleService",
    "SubjectPeriodOverrideAvailability",
    "SubjectPeriodOverrideResult",
    "SubjectPeriodOverrideService",
    "SubjectWorkflowActionService",
    "SubjectIdentifierMigrationBlockedError",
    "SubjectIdentifierMigrationConfirmationRequiredError",
    "SubjectIdentifierMigrationPreview",
    "SubjectIdentifierMigrationStalePlanError",
    "SubjectIdentifierPolicyMigrationService",
    "RandomizeSubject",
    "RandomizeSubjectCommand",
    "CorrectSubjectMilestone",
    "CorrectSubjectMilestoneCommand",
]

_MODULE_BY_NAME = {
    "AddRepeatingSubjectEventInstanceService": "apps.subject.application.services.add_repeating_event_instance",
    "SubjectBulkActionResult": "apps.subject.application.services.bulk_actions",
    "SubjectBulkActionService": "apps.subject.application.services.bulk_actions",
    "CreateSubjectService": "apps.subject.application.services.create_subject",
    "SubjectDuePeriodTransitionResult": "apps.subject.application.services.due_period_transition",
    "SubjectDuePeriodTransitionService": "apps.subject.application.services.due_period_transition",
    "SubjectEventCompletionService": "apps.subject.application.services.event_completion",
    "SubjectEventInstanceResyncResult": "apps.subject.application.services.event_instance_resync",
    "SubjectEventInstanceResyncService": "apps.subject.application.services.event_instance_resync",
    "SubjectEventTransitionService": "apps.subject.application.services.event_lifecycle",
    "SubjectPeriodLifecycleResult": "apps.subject.application.services.period_lifecycle",
    "SubjectPeriodLifecycleService": "apps.subject.application.services.period_lifecycle",
    "SubjectPeriodOverrideAvailability": "apps.subject.application.services.period_override",
    "SubjectPeriodOverrideResult": "apps.subject.application.services.period_override",
    "SubjectPeriodOverrideService": "apps.subject.application.services.period_override",
    "SubjectWorkflowActionService": "apps.subject.application.services.workflow_action",
    "SubjectIdentifierMigrationBlockedError": "apps.subject.application.services.identifier_policy_migration",
    "SubjectIdentifierMigrationConfirmationRequiredError": "apps.subject.application.services.identifier_policy_migration",
    "SubjectIdentifierMigrationPreview": "apps.subject.application.services.identifier_policy_migration",
    "SubjectIdentifierMigrationStalePlanError": "apps.subject.application.services.identifier_policy_migration",
    "SubjectIdentifierPolicyMigrationService": "apps.subject.application.services.identifier_policy_migration",
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
