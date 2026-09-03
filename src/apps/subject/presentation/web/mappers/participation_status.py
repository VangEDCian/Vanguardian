from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _

from apps.subject.application.services.participation_status import (
    SubjectParticipationDisplayStatus,
    SubjectParticipationStatusService,
)

DISPLAY_LABEL_BY_STATUS = {
    SubjectParticipationDisplayStatus.SCREEN_FAILURE: _("Screen Failure"),
    SubjectParticipationDisplayStatus.WAITING_FOR_RANDOMIZATION_SLOT: _(
        "Waiting for Randomization Slot"
    ),
    SubjectParticipationDisplayStatus.PENDING_RANDOMIZATION: _(
        "Pending Randomization"
    ),
    SubjectParticipationDisplayStatus.PENDING_ENROLLMENT: _("Pending Enrollment"),
}


def get_subject_participation_status_label(
    record,
    *,
    randomization_transition_facts=None,
):
    enrollment = _related_or_none(record, "enrollment")
    randomization = _related_or_none(record, "randomization")
    if getattr(enrollment, "deleted", False):
        enrollment = None
    if getattr(randomization, "deleted", False):
        randomization = None

    facts = randomization_transition_facts or {}
    status = SubjectParticipationStatusService.resolve(
        lifecycle_status=str(getattr(record, "lifecycle_status", "") or ""),
        enrollment_status=str(getattr(enrollment, "status", "") or ""),
        is_enrolled=bool(getattr(enrollment, "is_enrolled", False)),
        randomization_status=str(
            getattr(randomization, "randomization_status", "") or ""
        ),
        has_randomization_slot=bool(getattr(randomization, "slot_id", None)),
        randomization_scheme_status=str(
            facts.get("randomization.scheme.status") or ""
        ),
        available_randomization_slot_count=facts.get(
            "randomization.available_slot_count"
        ),
    )
    if status in DISPLAY_LABEL_BY_STATUS:
        return DISPLAY_LABEL_BY_STATUS[status]
    return record.get_lifecycle_status_display()


def _related_or_none(record, attribute_name):
    try:
        return getattr(record, attribute_name)
    except (AttributeError, ObjectDoesNotExist):
        return None


__all__ = ["get_subject_participation_status_label"]
