from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse

from apps.core.choices import SubjectLifecycleStatusChoices
from apps.subject.application.services.period_override import (
    SubjectPeriodOverrideService,
)
from apps.subject.domain import SubjectPeriodStatus
from apps.subject.infrastructure.repositories.period_lifecycle import (
    SubjectPeriodOverrideContext,
    SubjectPeriodState,
)
from apps.subject.presentation.web.views.period_override import (
    SubjectPeriodOverrideView,
)


class SubjectPeriodOverrideServiceTests(SimpleTestCase):
    def test_advances_period_without_changing_source_event_status(self):
        repository = _PeriodOverrideRepositoryStub(
            period_events=(
                SimpleNamespace(
                    event_instance_id=81,
                    event_definition_id=8,
                    event_code="VISIT8",
                    event_status="in_progress",
                    sequence_no=8,
                ),
            ),
        )
        pending_data_reader = _PendingDataSnapshotReaderStub()
        service = SubjectPeriodOverrideService(
            repository=repository,
            pending_data_snapshot_reader=pending_data_reader,
        )
        period_end_at = repository.current_time - timedelta(days=2)
        next_period_start_at = repository.current_time - timedelta(days=1)

        result = SubjectPeriodOverrideService.advance_to_next_period.__wrapped__(
            service,
            study_id=1,
            subject_id=20,
            actor_user_id=99,
            period_end_at=period_end_at,
            next_period_start_at=next_period_start_at,
            reason_code="paper_crf_delayed",
            reason_text="Paper CRF has not reached the site.",
            pending_data_acknowledged=True,
            clinical_transition_confirmed=True,
        )

        self.assertTrue(result.applied)
        self.assertEqual(result.override_id, 71)
        self.assertEqual(
            [period.status for period in repository.periods],
            [SubjectPeriodStatus.COMPLETED, SubjectPeriodStatus.ACTIVE],
        )
        self.assertEqual(repository.source_event_status, "in_progress")
        self.assertEqual(repository.override_calls[0]["source_event_status"], "in_progress")
        self.assertEqual(
            repository.override_calls[0]["pending_data_snapshot"][
                "pending_form_count"
            ],
            1,
        )
        self.assertEqual(pending_data_reader.event_instance_ids, [(81,)])
        self.assertEqual(repository.period_end_records[0]["occurred_at"], period_end_at)
        self.assertEqual(
            repository.period_start_records[0]["occurred_at"],
            next_period_start_at,
        )
        self.assertEqual(len(repository.transition_calls), 2)

    def test_rejects_override_when_washout_duration_is_not_satisfied(self):
        repository = _PeriodOverrideRepositoryStub(washout_days=14)
        service = SubjectPeriodOverrideService(repository=repository)

        result = SubjectPeriodOverrideService.advance_to_next_period.__wrapped__(
            service,
            study_id=1,
            subject_id=20,
            actor_user_id=99,
            period_end_at=repository.current_time - timedelta(days=13),
            next_period_start_at=repository.current_time,
            reason_code="paper_crf_delayed",
            reason_text="Paper CRF delayed.",
            pending_data_acknowledged=True,
            clinical_transition_confirmed=True,
        )

        self.assertFalse(result.applied)
        self.assertEqual(result.reason, "washout_not_satisfied")
        self.assertEqual(repository.override_calls, [])
        self.assertEqual(repository.transition_calls, [])

    def test_requires_pending_data_and_clinical_confirmations(self):
        repository = _PeriodOverrideRepositoryStub()
        service = SubjectPeriodOverrideService(repository=repository)

        result = SubjectPeriodOverrideService.advance_to_next_period.__wrapped__(
            service,
            study_id=1,
            subject_id=20,
            actor_user_id=99,
            period_end_at=repository.current_time,
            next_period_start_at=repository.current_time,
            reason_code="paper_crf_delayed",
            reason_text="Paper CRF delayed.",
            pending_data_acknowledged=False,
            clinical_transition_confirmed=True,
        )

        self.assertFalse(result.applied)
        self.assertEqual(result.reason, "pending_data_acknowledgement_required")

    def test_availability_exposes_current_and_next_treatments(self):
        service = SubjectPeriodOverrideService(
            repository=_PeriodOverrideRepositoryStub(),
        )

        availability = service.get_availability(subject_id=20)

        self.assertTrue(availability.available)
        self.assertEqual(availability.current_treatment_code, "TREATMENT_A")
        self.assertEqual(availability.next_treatment_code, "TREATMENT_B")
        self.assertEqual(availability.source_event_status, "in_progress")


class SubjectPeriodOverrideViewTests(SimpleTestCase):
    def test_uses_dedicated_permission_and_validated_override_details(self):
        self.assertEqual(
            SubjectPeriodOverrideView.permission_required,
            "SUBJECT.PERIOD_OVERRIDE",
        )
        next_url = reverse(
            "subject:subject_detail",
            kwargs={"study_id": 1, "subject_id": 20},
        )
        request = RequestFactory().post(
            "/period-transition/override/",
            data={
                "next": next_url,
                "period_end_at": "2026-07-15T09:00",
                "next_period_start_at": "2026-07-30T09:00",
                "reason_code": "paper_crf_delayed",
                "reason_text": "Paper CRF has not reached the site.",
                "pending_data_acknowledged": "on",
                "clinical_transition_confirmed": "on",
            },
        )
        request.user = SimpleNamespace(pk=99)
        view = SubjectPeriodOverrideView()
        view.service_class = _SuccessfulOverrideService
        _SuccessfulOverrideService.calls = []

        with patch(
            "apps.subject.presentation.web.views.period_override.messages"
        ) as messages:
            response = view.post(request, study_id=1, subject_id=20)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], next_url)
        self.assertEqual(len(_SuccessfulOverrideService.calls), 1)
        self.assertEqual(
            _SuccessfulOverrideService.calls[0]["reason_code"],
            "paper_crf_delayed",
        )
        self.assertTrue(
            _SuccessfulOverrideService.calls[0]["pending_data_acknowledged"],
        )
        self.assertTrue(
            _SuccessfulOverrideService.calls[0]["clinical_transition_confirmed"],
        )
        messages.success.assert_called_once()


class _PeriodOverrideRepositoryStub:
    def __init__(self, *, washout_days=None, period_events=()):
        self.current_time = datetime(2026, 7, 30, 9, 0, tzinfo=timezone.utc)
        self.source_event_status = "in_progress"
        self.period_events = period_events
        self.periods = [
            _period(
                period_id=1,
                period_no=1,
                status=SubjectPeriodStatus.ACTIVE,
                treatment_code="TREATMENT_A",
                end_event_instance_id=81,
                washout_days=washout_days,
            ),
            _period(
                period_id=2,
                period_no=2,
                status=SubjectPeriodStatus.PLANNED,
                treatment_code="TREATMENT_B",
            ),
        ]
        self.override_calls = []
        self.transition_calls = []
        self.period_end_records = []
        self.washout_end_records = []
        self.period_start_records = []

    def now(self):
        return self.current_time

    def get_manual_override_context(self, *, subject_id):
        return SubjectPeriodOverrideContext(
            current_period=self.periods[0],
            next_period=self.periods[1],
            source_event_status=self.source_event_status,
        )

    def get_subject_lifecycle_status(self, *, subject_id):
        return SubjectLifecycleStatusChoices.ACTIVE

    def get_subject_lifecycle_status_for_update(self, *, study_id, subject_id):
        return SubjectLifecycleStatusChoices.ACTIVE

    def list_periods_for_update(self, *, subject_id):
        return list(self.periods)

    def get_event_status(self, *, event_instance_id):
        return self.source_event_status

    def list_period_event_snapshots(self, *, period):
        return self.period_events

    def create_transition_override(self, **kwargs):
        self.override_calls.append(kwargs)
        return 71

    def record_period_end(self, **kwargs):
        self.period_end_records.append(kwargs)

    def record_washout_end(self, **kwargs):
        self.washout_end_records.append(kwargs)

    def transition_period(self, *, period, to_status, **kwargs):
        updated_period = _period(
            period_id=period.id,
            period_no=period.period_no,
            status=to_status,
            treatment_code=period.treatment_code,
            end_event_instance_id=period.end_event_instance_id,
            washout_days=period.washout_days,
        )
        self.periods = [
            updated_period if candidate.id == period.id else candidate
            for candidate in self.periods
        ]
        self.transition_calls.append(
            {
                "period_id": period.id,
                "from_status": period.status,
                "to_status": to_status,
                **kwargs,
            }
        )
        return updated_period

    def record_period_start(self, **kwargs):
        self.period_start_records.append(kwargs)


class _SuccessfulOverrideService:
    calls = []

    def advance_to_next_period(self, **kwargs):
        type(self).calls.append(kwargs)
        return SimpleNamespace(
            applied=True,
            reason="manual_period_transition_override",
        )


class _PendingDataSnapshotReaderStub:
    def __init__(self):
        self.event_instance_ids = []

    def __call__(self, *, subject_id, event_instances):
        self.event_instance_ids.append(
            tuple(event["event_instance_id"] for event in event_instances)
        )
        return {
            "pending_form_count": 1,
            "pending_forms": [
                {
                    "event_instance_id": 81,
                    "event_code": "VISIT8",
                    "page_status": "in_progress",
                }
            ],
        }


def _period(
    *,
    period_id,
    period_no,
    status,
    treatment_code,
    end_event_instance_id=None,
    washout_days=None,
):
    return SubjectPeriodState(
        id=period_id,
        subject_id=20,
        period_no=period_no,
        status=status,
        start_event_instance_id=None,
        end_event_instance_id=end_event_instance_id,
        washout_days=washout_days,
        transition_rule_code=None,
        treatment_code=treatment_code,
    )
