from django.db import models
from django.utils.translation import gettext_lazy as _


class ReconcileValidationRunSourceChoices(models.TextChoices):
    SUBMIT_FOR_REVIEW = "SUBMIT_FOR_REVIEW", _("Submit for review")
    VALIDATION_ISSUE_ACKNOWLEDGEMENT = "VALIDATION_ISSUE_ACKNOWLEDGEMENT", _("Validation issue acknowledgement")
