from django.db import models
from django.utils.translation import gettext_lazy as _


class EventDefinitionTypeChoices(models.TextChoices):
    VISIT_BASED = "visit_based", _("Visit based")
    COMMON = "common", _("Common")


class EventDefinitionTimingModeChoices(models.TextChoices):
    SCHEDULED = "scheduled", _("Scheduled")
    UNSCHEDULED = "unscheduled", _("Unscheduled")
    CONDITIONAL = "conditional", _("Conditional")


class EventInstanceStatusChoices(models.TextChoices):
    NOT_READY = "not_ready", _("Not ready")
    PLANNED = "planned", _("Planned")
    OPEN = "open", _("Open")
    IN_PROGRESS = "in_progress", _("In progress")
    COMPLETED = "completed", _("Completed")
    VERIFIED = "verified", _("Verified")
    LOCKED = "locked", _("Locked")
    SKIPPED = "skipped", _("Skipped")
    CANCELLED = "cancelled", _("Cancelled")
