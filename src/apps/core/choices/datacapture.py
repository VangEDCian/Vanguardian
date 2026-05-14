from django.db import models
from django.utils.translation import gettext_lazy as _


class DataCapturePageStateStatusChoices(models.TextChoices):
    NOT_STARTED = "not_started", _("Not started")
    IN_PROGRESS = "in_progress", _("In progress")
    SUBMITTED = "submitted", _("Submitted")
    UNDER_REVIEW = "under_review", _("Under review")
    CORRECTION_REQUIRED = "correction_required", _("Correction required")
    VERIFIED = "verified", _("Verified")
    LOCKED = "locked", _("Locked")
    FINALIZED = "finalized", _("Finalized")


class DataCapturePageEntryStatusChoices(models.TextChoices):
    DRAFT = "draft", _("Draft")
    SUBMITTED = "submitted", _("Submitted")
    ACCEPTED = "accepted", _("Accepted")
    REJECTED = "rejected", _("Rejected")
    SUPERSEDED = "superseded", _("Superseded")
    CANCELLED = "cancelled", _("Cancelled")


class DataCaptureFieldReviewStatusChoices(models.TextChoices):
    NOT_REVIEWED = "not_reviewed", _("Not reviewed")
    REVIEWED = "reviewed", _("Reviewed")
    VERIFIED = "verified", _("Verified")
    QUERIED = "queried", _("Queried")
    CORRECTION_REQUIRED = "correction_required", _("Correction required")
    STALE = "stale", _("Stale")
    WAIVED = "waived", _("Waived")


class DataCaptureFieldReviewTypeChoices(models.TextChoices):
    DATA_REVIEW = "data_review", _("Data review")
    SDV = "sdv", _("SDV")
    MEDICAL_REVIEW = "medical_review", _("Medical review")
    PI_VERIFY = "pi_verify", _("PI verify")
    ELIGIBILITY_VERIFY = "eligibility_verify", _("Eligibility verify")
