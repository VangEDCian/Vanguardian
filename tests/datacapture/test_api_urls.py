from django.test import SimpleTestCase
from django.urls import reverse


class DataCaptureApiUrlTests(SimpleTestCase):
    def test_datacapture_api_urls_use_api_prefix(self):
        kwargs = {
            "study_id": 1,
            "subject_id": 2,
            "visit_id": 3,
            "crf_template_id": 4,
        }

        self.assertEqual(
            reverse("datacapture:page_save", kwargs=kwargs),
            "/api/studies/1/subjects/2/events/3/forms/4/save/",
        )
        self.assertEqual(
            reverse("datacapture:page_submit", kwargs=kwargs),
            "/api/studies/1/subjects/2/events/3/forms/4/submit/",
        )
        self.assertEqual(
            reverse("datacapture:page_delete_draft", kwargs=kwargs),
            "/api/studies/1/subjects/2/events/3/forms/4/delete-draft/",
        )
