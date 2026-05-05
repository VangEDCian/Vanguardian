from django.db import models
from django.utils.translation import gettext_lazy as _


class DataCapturePageStateStatusChoices(models.TextChoices):
    DRAFT = "draft", _("Draft")
    SUBMITTED = "submitted", _("Submitted")
    IN_REVIEW = "in_review", _("In review")
    VERIFIED = "verified", _("Verified")
    FINALIZED = "finalized", _("Finalized")
    LOCKED = "locked", _("Locked")
    CANCELED = "canceled", _("Canceled")


class DataCapturePageEntryStatusChoices(models.TextChoices):
    DRAFT = "draft", _("Draft")
    SUBMITTED = "submitted", _("Submitted")
    SUPERSEDED = "superseded", _("Superseded")
    CANCELED = "canceled", _("Canceled")
