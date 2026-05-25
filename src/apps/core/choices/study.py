from django.db import models
from django.utils.translation import gettext_lazy as _


class EventDefinitionTypeChoices(models.TextChoices):
    VISIT_BASED = "visit_based", _("Visit based")
    COMMON = "common", _("Common")
    OPERATIONAL = "operational", _("Operational")


class EventDefinitionTimingModeChoices(models.TextChoices):
    SCHEDULED = "scheduled", _("Scheduled")
    UNSCHEDULED = "unscheduled", _("Unscheduled")
    CONDITIONAL = "conditional", _("Conditional")


class EventDefinitionCategoryChoices(models.TextChoices):
    SCREENING = "screening", _("Screening")
    RANDOMIZATION = "randomization", _("Randomization")
    TREATMENT = "treatment", _("Treatment")
    WASHOUT = "washout", _("Washout")
    FOLLOW_UP = "follow_up", _("Follow up")
    EOS = "eos", _("End of study")
    UNSCHEDULED = "unscheduled", _("Unscheduled")


class EventExecutionModeChoices(models.TextChoices):
    FORM_ENTRY = "form_entry", _("Form entry")
    WORKFLOW_ACTION = "workflow_action", _("Workflow action")
    HYBRID = "hybrid", _("Hybrid")


class EventTransitionTypeChoices(models.TextChoices):
    SEQUENTIAL = "sequential", _("Sequential")
    CONDITIONAL = "conditional", _("Conditional")


class EventTransitionConditionScopeChoices(models.TextChoices):
    SUBJECT = "subject", _("Subject")
    SUBJECT_EVENT = "subject_event", _("Subject event")
    SUBJECT_PERIOD = "subject_period", _("Subject period")
    RANDOMIZATION = "randomization", _("Randomization")
    ELIGIBILITY = "eligibility", _("Eligibility")
    NOT_ELIGIBLE = "not_eligible", _("Not eligible")


class StudyConditionDefinitionScopeChoices(models.TextChoices):
    SUBJECT = "subject", _("Subject")
    EVENT = "event", _("Event")
    ELIGIBILITY = "eligibility", _("Eligibility")
    RANDOMIZATION = "randomization", _("Randomization")
    PERIOD = "period", _("Period")
    PAGE = "page", _("Page")


class StudyConditionDefinitionStatusChoices(models.TextChoices):
    DRAFT = "draft", _("Draft")
    ACTIVE = "active", _("Active")
    RETIRED = "retired", _("Retired")


class EventInstanceStatusChoices(models.TextChoices):
    NOT_READY = "not_ready", _("Not ready")
    PLANNED = "planned", _("Planned")
    OPEN = "open", _("Open")
    IN_PROGRESS = "in_progress", _("In progress")
    COMPLETED = "completed", _("Completed")
    VERIFIED = "verified", _("Verified")
    LOCKED = "locked", _("Locked")
    FINALIZED = "finalized", _("Finalized")
    SKIPPED = "skipped", _("Skipped")
    CANCELLED = "cancelled", _("Cancelled")


class RandomizationSchemeStatusChoice(models.TextChoices):
    DRAFT = "draft", _("Draft")
    ACTIVE = "active", _("Active")
    CLOSED = "closed", _("Closed")
    RETRIED = "retried", _("Retried")


class RandomizationSlotStatusChoice(models.TextChoices):
    AVAILABLE = "available", _("Available")
    ASSIGNED = "assigned", _("Assigned")
    VOID = "void", _("Void")


class EligibilityAssessmentTypeChoices(models.TextChoices):
    PRESCREENING = "PRESCREENING", _("Prescreening")
    SCREENING = "SCREENING", _("Screening")
    RESCREENING = "RESCREENING", _("Rescreening")


class EligibilityResultChoices(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    ELIGIBLE = "ELIGIBLE", _("Eligible")
    NOT_ELIGIBLE = "NOT_ELIGIBLE", _("Not eligible")
    NOT_ASSESSED = "NOT_ASSESSED", _("Not assessed")


class EligibilityAssessmentStatusChoices(models.TextChoices):
    DRAFT = "DRAFT", _("Draft")
    FINAL = "FINAL", _("Final")
    STALE = "STALE", _("Stale")
    RETRACTED = "RETRACTED", _("Retracted")
    SUPERSEDED = "SUPERSEDED", _("Superseded")


class EligibilityCriterionTypeChoices(models.TextChoices):
    INCLUSION = "INCLUSION", _("Inclusion")
    EXCLUSION = "EXCLUSION", _("Exclusion")
    OTHER = "OTHER", _("Other")
