from django.db import models
from django.utils.translation import gettext_lazy as _


class EventFormEntryModeChoices(models.TextChoices):
    SINGLE = "single", _("Single")
    DOUBLE_ENTRY = "double_entry", _("Double Entry")
    REVIEW_ONLY = "review_only", _("Review Only")
    VERIFICATION = "verification", _("Verification")
    QUERY_RESPONSE = "query_response", _("Query Response")
