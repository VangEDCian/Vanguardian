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

    def test_uses_period_2_event_status_when_actual_milestones_are_not_recorded(self):
        period_1 = _period(period_no=1, treatment_code="NANOKINE", milestones=[])
        period_1.end_event_status = "completed"
        period_2 = _period(period_no=2, treatment_code="EPREX_4000U", milestones=[])
        period_2.start_event_status = "open"
        period_2.kit_code = "R-NNG31-001"
        service = SubjectTreatmentTimelineService(
            repository=_TimelineRepositoryStub(
                randomization=SimpleNamespace(randomization_sequence="SEQ_N_E"),
                periods=[period_1, period_2],
            )
        )

        result = service.get_current_subject_treatment(subject_id=20)

        self.assertEqual(result.status, "Active")
        self.assertEqual(result.treatment_code, "EPREX_4000U")
        self.assertEqual(result.kit_code, "R-NNG31-001")

    def test_maps_current_treatment_for_subject_list_in_batch(self):
        period_1 = _period(period_no=1, treatment_code="NANOKINE", milestones=[])
        period_1.end_event_status = "completed"
        period_2 = _period(period_no=2, treatment_code="EPREX_4000U", milestones=[])
        period_2.start_event_status = "open"
        service = SubjectTreatmentTimelineService(
            repository=_BatchTimelineRepositoryStub(
                randomizations={20: SimpleNamespace(randomization_sequence="SEQ_N_E")},
                periods_by_subject_id={20: [period_1, period_2]},
            )
        )

        result = service.map_current_subject_treatment_by_subject_id(subject_ids=(20, 21))

        self.assertEqual(result[20].treatment_code, "EPREX_4000U")
        self.assertEqual(result[21].status, "Not randomized")


def _period(*, period_no, treatment_code, milestones):
    return SimpleNamespace(
        period_no=period_no,
        treatment_code=treatment_code,
        status="Planned",
        sequence_period_id=period_no,
        start_event_instance_id=None,
        end_event_instance_id=None,
        milestones=tuple(milestones),
        kit_code=None,
        start_event_status=None,
        end_event_status=None,
    )


class _TimelineRepositoryStub:
    def __init__(self, *, randomization, periods):
        self.randomization = randomization
        self.periods = periods

    def get_randomization(self, *, subject_id):
        return self.randomization

    def list_periods(self, *, subject_id):
        return self.periods


class _BatchTimelineRepositoryStub:
    def __init__(self, *, randomizations, periods_by_subject_id):
        self.randomizations = randomizations
        self.periods_by_subject_id = periods_by_subject_id

    def get_randomizations(self, *, subject_ids):
        return {
            subject_id: self.randomizations[subject_id]
            for subject_id in subject_ids
            if subject_id in self.randomizations
        }

    def list_periods_by_subject_id(self, *, subject_ids):
        return {
            subject_id: self.periods_by_subject_id[subject_id]
            for subject_id in subject_ids
            if subject_id in self.periods_by_subject_id
        }
