from datetime import datetime, timezone
from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase

from apps.crf.models import CrfTemplate
from apps.datacapture.application.services.pending_period_data import (
    PendingPeriodDataSnapshotService,
)
from apps.datacapture.infrastructure.repositories.pending_period_data import (
    DjangoPendingPeriodDataRepository,
)
from apps.datacapture.models import DataCapturePageState
from apps.study.models import EventDefinition, EventFormBinding, Site, Study
from apps.subject.models import Subject, SubjectEventInstance


class PendingPeriodDataSnapshotServiceTests(SimpleTestCase):
    def test_builds_audit_snapshot_from_pending_forms(self):
        repository = _PendingPeriodDataRepositoryStub()

        snapshot = PendingPeriodDataSnapshotService(
            repository=repository,
        ).build_snapshot(
            subject_id=20,
            event_instances=(
                {
                    "event_instance_id": 81,
                    "event_definition_id": 8,
                    "event_code": "VISIT8",
                    "event_status": "in_progress",
                    "sequence_no": 8,
                },
            ),
        )

        self.assertEqual(snapshot["pending_form_count"], 2)
        self.assertEqual(
            [form["page_status"] for form in snapshot["pending_forms"]],
            ["not_started", "correction_required"],
        )
        self.assertEqual(snapshot["pending_forms"][0]["event_code"], "VISIT8")


class DjangoPendingPeriodDataRepositoryTests(TestCase):
    def setUp(self):
        self.now = datetime(2026, 7, 30, 9, 0, tzinfo=timezone.utc)
        self.study = Study.objects.create(
            created_at=self.now,
            updated_at=self.now,
            deleted=False,
            code="PENDING_DATA",
            name="Pending data",
        )
        self.site = Site.objects.create(
            created_at=self.now,
            updated_at=self.now,
            deleted=False,
            study=self.study,
            code="SITE01",
            name="Site 01",
        )
        self.subject = Subject.objects.create(
            created_at=self.now,
            updated_at=self.now,
            deleted=False,
            study=self.study,
            site=self.site,
            subject_code="SUBJ-001",
            screening_code="SCR-001",
            current_sequence=1,
        )
        self.event_definition = EventDefinition.objects.create(
            created_at=self.now,
            updated_at=self.now,
            deleted=False,
            study=self.study,
            study_version="v1.0",
            code="VISIT8",
            name="Visit 8",
            event_type="visit_based",
            event_category="treatment",
            sequence_no=8,
            is_enabled=True,
        )
        self.event_instance = SubjectEventInstance.objects.create(
            created_at=self.now,
            updated_at=self.now,
            deleted=False,
            study=self.study,
            subject=self.subject,
            event_definition=self.event_definition,
            study_version="v1.0",
            status="in_progress",
        )

    def test_includes_unmaterialized_form_and_excludes_submitted_form(self):
        pending_binding = self._create_binding(code="PENDING", display_order=1)
        submitted_binding = self._create_binding(code="SUBMITTED", display_order=2)
        DataCapturePageState.objects.create(
            created_at=self.now,
            updated_at=self.now,
            deleted=False,
            status="submitted",
            crf_template=submitted_binding.form_definition,
            event_form_binding=submitted_binding,
            subject=self.subject,
            visit=self.event_instance,
        )

        pending_forms = DjangoPendingPeriodDataRepository().list_pending_form_states(
            subject_id=self.subject.pk,
            event_instances=(
                {
                    "event_instance_id": self.event_instance.pk,
                    "event_definition_id": self.event_definition.pk,
                    "event_code": "VISIT8",
                    "event_status": "in_progress",
                    "sequence_no": 8,
                },
            ),
        )

        self.assertEqual(len(pending_forms), 1)
        self.assertEqual(
            pending_forms[0].event_form_binding_id,
            pending_binding.pk,
        )
        self.assertEqual(pending_forms[0].page_status, "not_started")

    def _create_binding(self, *, code, display_order):
        crf_template = CrfTemplate.objects.create(
            created_at=self.now,
            updated_at=self.now,
            deleted=False,
            code=code,
            version="1.0",
            study=self.study,
            is_active=True,
        )
        return EventFormBinding.objects.create(
            created_at=self.now,
            updated_at=self.now,
            deleted=False,
            study=self.study,
            study_version="v1.0",
            event_definition=self.event_definition,
            form_definition=crf_template,
            display_order=display_order,
            is_required=True,
            is_enabled=True,
        )


class _PendingPeriodDataRepositoryStub:
    def list_pending_form_states(self, *, subject_id, event_instances):
        return (
            SimpleNamespace(
                event_instance_id=81,
                event_code="VISIT8",
                event_status="in_progress",
                event_form_binding_id=101,
                crf_template_id=201,
                repeat_index=1,
                page_state_id=None,
                page_status="not_started",
            ),
            SimpleNamespace(
                event_instance_id=81,
                event_code="VISIT8",
                event_status="in_progress",
                event_form_binding_id=102,
                crf_template_id=202,
                repeat_index=1,
                page_state_id=301,
                page_status="correction_required",
            ),
        )
