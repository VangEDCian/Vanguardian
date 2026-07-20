from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Prefetch

from apps.subject.models import Subject, SubjectEventInstance, SubjectPeriod

_RANDOMIZATION_EVENT_CATEGORY = "randomization"


class DjangoSubjectSummaryRepository:
    def get_subject_summary_snapshot(
        self,
        *,
        study_id: int,
        subject_id: int,
        snapshot_class,
        randomization_event_class,
        period_class,
    ):
        randomization_events = (
            SubjectEventInstance.objects.select_related("event_definition")
            .filter(
                deleted=False,
                event_definition__event_category__iexact=_RANDOMIZATION_EVENT_CATEGORY,
            )
            .order_by("-opened_at", "-created_at", "-id")
        )
        subject_periods = SubjectPeriod.objects.filter(deleted=False).order_by("period_no", "id")
        subject = (
            Subject.objects.filter(study_id=study_id, pk=subject_id, deleted=False)
            .select_related(
                "site",
                "study",
                "enrollment",
                "randomization",
                "randomization__scheme",
                "randomization__arm",
                "randomization__slot",
            )
            .prefetch_related(
                Prefetch(
                    "event_instances",
                    queryset=randomization_events,
                    to_attr="summary_randomization_events",
                ),
                Prefetch("periods", queryset=subject_periods, to_attr="summary_periods"),
            )
            .first()
        )
        if subject is None:
            return None

        enrollment = self._get_related_or_none(subject, "enrollment")
        randomization = self._get_related_or_none(subject, "randomization")
        randomization_event = self._build_randomization_event(
            subject=subject,
            randomization_event_class=randomization_event_class,
        )

        return snapshot_class(
            subject_id=subject.pk,
            study_id=subject.study_id,
            site_id=subject.site_id,
            study_code=getattr(subject.study, "code", ""),
            site_code=getattr(subject.site, "code", ""),
            screening_code=subject.screening_code or "",
            subject_code=subject.subject_code or "",
            screening_date=subject.created_at,
            enrollment_is_enrolled=bool(getattr(enrollment, "is_enrolled", False)),
            enrollment_status=getattr(enrollment, "status", "") if enrollment is not None else "",
            enrollment_date=getattr(enrollment, "enrollment_date", None) if enrollment is not None else None,
            enrollment_status_datetime=(
                getattr(enrollment, "status_datetime", None) if enrollment is not None else None
            ),
            enrollment_reason_code=(
                getattr(enrollment, "status_reason_code", "") if enrollment is not None else ""
            ),
            enrollment_reason_text=(
                getattr(enrollment, "status_reason_text", "") if enrollment is not None else ""
            ),
            randomization_status=(
                getattr(randomization, "randomization_status", "") if randomization is not None else ""
            ),
            randomization_datetime=(
                getattr(randomization, "randomization_datetime", None) if randomization is not None else None
            ),
            randomization_number=(
                getattr(randomization, "randomization_number", "") if randomization is not None else ""
            ),
            randomization_scheme_code=(
                getattr(getattr(randomization, "scheme", None), "code", "") if randomization is not None else ""
            ),
            randomization_arm_name=(
                getattr(getattr(randomization, "arm", None), "arm_name", "") if randomization is not None else ""
            ),
            randomization_slot_sequence=(
                getattr(getattr(randomization, "slot", None), "sequence_no", None)
                if randomization is not None
                else None
            ),
            randomization_event=randomization_event,
            periods=tuple(
                period_class(
                    period_no=period.period_no,
                    treatment_code=period.treatment_code,
                    kit_code=period.kit_code or "",
                )
                for period in getattr(subject, "summary_periods", ())
            ),
        )

    @staticmethod
    def _get_related_or_none(subject, related_name: str):
        try:
            return getattr(subject, related_name)
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def _build_randomization_event(*, subject, randomization_event_class):
        events = getattr(subject, "summary_randomization_events", None) or ()
        if not events:
            return None
        event = events[0]
        return randomization_event_class(
            event_name=(
                getattr(event, "event_name_snapshot", "")
                or getattr(getattr(event, "event_definition", None), "name", "")
                or getattr(event, "event_code_snapshot", "")
            ),
            status=getattr(event, "status", ""),
            opened_at=getattr(event, "opened_at", None),
            planned_date=getattr(event, "planned_date", None),
        )


__all__ = ["DjangoSubjectSummaryRepository"]
