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

    def test_returns_active_from_authoritative_period_status(self):
        period = _period(
            period_no=1,
            treatment_code="EPREX",
            milestones=[],
            status="active",
        )
        service = SubjectTreatmentTimelineService(
            repository=_TimelineRepositoryStub(
                randomization=SimpleNamespace(randomization_sequence="SEQ_E_N"),
                periods=[period],
            )
        )
        result = service.get_current_subject_treatment(subject_id=20)

        self.assertEqual(result.status, "Active")
        self.assertEqual(result.treatment_code, "EPREX")

    def test_open_future_visit_does_not_activate_planned_period(self):
        period_1 = _period(
            period_no=1,
            treatment_code="NANOKINE",
            milestones=[],
            status="active",
        )
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
        self.assertEqual(result.treatment_code, "NANOKINE")
        self.assertIsNone(result.kit_code)

    def test_washout_status_reports_last_and_next_treatment(self):
        period_1 = _period(
            period_no=1,
            treatment_code="NANOKINE",
            milestones=[],
            status="washout",
        )
        period_2 = _period(
            period_no=2,
            treatment_code="EPREX_4000U",
            milestones=[],
        )
        service = SubjectTreatmentTimelineService(
            repository=_TimelineRepositoryStub(
                randomization=SimpleNamespace(randomization_sequence="SEQ_N_E"),
                periods=[period_1, period_2],
            )
        )

        result = service.get_current_subject_treatment(subject_id=20)

        self.assertEqual(result.status, "Washout")
        self.assertEqual(result.last_treatment, "NANOKINE")
        self.assertEqual(result.next_treatment, "EPREX_4000U")

    def test_maps_current_treatment_for_subject_list_in_batch(self):
        period_1 = _period(
            period_no=1,
            treatment_code="NANOKINE",
            milestones=[],
            status="completed",
        )
        period_2 = _period(
            period_no=2,
            treatment_code="EPREX_4000U",
            milestones=[],
            status="active",
        )
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


def _period(*, period_no, treatment_code, milestones, status="planned"):
    return SimpleNamespace(
        period_no=period_no,
        treatment_code=treatment_code,
        status=status,
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
