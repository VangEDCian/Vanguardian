from datetime import datetime, timezone
from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.subject.application.services.treatment_timeline import SubjectTreatmentTimelineService


class SubjectTreatmentTimelineServiceTests(SimpleTestCase):
    def test_returns_not_randomized_before_assignment(self):
        service = SubjectTreatmentTimelineService(repository=_TimelineRepositoryStub(randomization=None, periods=[]))
        result = service.get_current_subject_treatment(subject_id=20)

        self.assertEqual(result.status, "Not randomized")
        self.assertIsNone(result.treatment_code)

    def test_returns_planned_treatment_after_randomization_before_dosing(self):
        period = _period(period_no=1, treatment_code="EPREX", milestones=[])
        service = SubjectTreatmentTimelineService(
            repository=_TimelineRepositoryStub(
                randomization=SimpleNamespace(randomization_sequence="SEQ_E_N"),
                periods=[period],
            )
        )
        result = service.get_current_subject_treatment(subject_id=20)

        self.assertEqual(result.status, "Planned")
        self.assertEqual(result.next_treatment, "EPREX")

    def test_returns_active_only_after_actual_dose_milestone(self):
        as_of = datetime(2026, 5, 20, 9, 0, tzinfo=timezone.utc)
        period = _period(
            period_no=1,
            treatment_code="EPREX",
            milestones=[SimpleNamespace(milestone_code="DOSE_ACTUAL", actual_at=datetime(2026, 5, 20, 8, 0, tzinfo=timezone.utc))],
        )
        service = SubjectTreatmentTimelineService(
            repository=_TimelineRepositoryStub(
                randomization=SimpleNamespace(randomization_sequence="SEQ_E_N"),
                periods=[period],
            )
        )
        result = service.get_current_subject_treatment(subject_id=20, as_of=as_of)

        self.assertEqual(result.status, "Active")
        self.assertEqual(result.treatment_code, "EPREX")


def _period(*, period_no, treatment_code, milestones):
    return SimpleNamespace(
        period_no=period_no,
        treatment_code=treatment_code,
        status="Planned",
        sequence_period_id=period_no,
        start_event_instance_id=None,
        end_event_instance_id=None,
        milestones=tuple(milestones),
    )


class _TimelineRepositoryStub:
    def __init__(self, *, randomization, periods):
        self.randomization = randomization
        self.periods = periods

    def get_randomization(self, *, subject_id):
        return self.randomization

    def list_periods(self, *, subject_id):
        return self.periods
