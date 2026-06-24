from pathlib import Path

from django.test import SimpleTestCase


class DatacaptureUnsavedChangesGuardStaticTests(SimpleTestCase):
    def test_behavior_runtime_marks_initial_auto_computed_payload_clean(self):
        source = (
            Path(__file__).resolve().parents[2]
            / "src/staticfiles/datacapture/js/subject-detail-behavior-runtime.js"
        ).read_text()

        self.assertIn(
            "window.DatacaptureUnsavedChangesGuard?.markCurrentPayloadClean?.();",
            source,
        )
