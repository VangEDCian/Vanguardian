from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.datacapture.application.commands import (
    DeleteDraftPageCommand,
    SavePageCommand,
    SubmitPageCommand,
)
from apps.datacapture.application.exceptions import (
    DataCaptureSubjectLifecycleError,
)
from apps.datacapture.application.services.form_instances import (
    DataCaptureFormInstanceService,
)
from apps.datacapture.application.services.save_submit_page import (
    DataCaptureSaveSubmitPageService,
)


class SubjectLifecycleCaptureGuardTests(SimpleTestCase):
    def setUp(self):
        self.reader = _DeniedCaptureEligibilityReader()
        self.service = DataCaptureSaveSubmitPageService(
            repository=SimpleNamespace(),
            governance_lock_read_repository=SimpleNamespace(),
            subject_event_lifecycle_adapter=SimpleNamespace(),
            subject_capture_eligibility_reader=self.reader,
            reconcile_data_query_write_service=SimpleNamespace(),
        )

    def test_save_submit_and_delete_are_rejected_before_capture_writes(self):
        commands = (
            (
                DataCaptureSaveSubmitPageService.save,
                SavePageCommand(
                    subject_id=20,
                    visit_id=30,
                    crf_template_id=40,
                    data="{}",
                ),
            ),
            (
                DataCaptureSaveSubmitPageService.submit,
                SubmitPageCommand(
                    subject_id=20,
                    visit_id=30,
                    crf_template_id=40,
                    data="{}",
                ),
            ),
            (
                DataCaptureSaveSubmitPageService.delete_latest_draft,
                DeleteDraftPageCommand(
                    subject_id=20,
                    visit_id=30,
                    crf_template_id=40,
                ),
            ),
        )

        for method, command in commands:
            with (
                self.subTest(method=method.__name__),
                self.assertRaises(DataCaptureSubjectLifecycleError),
            ):
                method.__wrapped__(self.service, command)

        self.assertEqual(self.reader.calls, [(20, 30), (20, 30), (20, 30)])

    def test_repeated_form_creation_is_rejected_before_binding_lookup(self):
        binding_reader = _BindingReaderSpy()
        service = DataCaptureFormInstanceService(
            binding_reader=binding_reader,
            repository=SimpleNamespace(),
            crf_context_adapter=SimpleNamespace(),
            config_reader=SimpleNamespace(),
            label_renderer=SimpleNamespace(),
            audit_context_adapter=SimpleNamespace(),
            subject_capture_eligibility_reader=self.reader,
        )

        with self.assertRaises(DataCaptureSubjectLifecycleError):
            DataCaptureFormInstanceService.create_form_instance.__wrapped__(
                service,
                subject_id=20,
                visit_id=30,
                event_form_binding_id=50,
            )

        self.assertEqual(binding_reader.calls, [])


class _DeniedCaptureEligibilityReader:
    def __init__(self):
        self.calls = []

    def get(self, *, subject_id, event_instance_id):
        self.calls.append((subject_id, event_instance_id))
        return SimpleNamespace(
            allowed=False,
            reason="subject_lifecycle_blocks_capture",
        )


class _BindingReaderSpy:
    def __init__(self):
        self.calls = []

    def get_binding_snapshot(self, *, binding_id):
        self.calls.append(binding_id)
        return None
