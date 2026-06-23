from django.templatetags.static import static
from django.test import SimpleTestCase


class VersionedStaticFilesStorageTests(SimpleTestCase):
    def test_static_tag_appends_file_version_query(self):
        url = static("subject/css/subject_detail.css")

        self.assertTrue(url.startswith("/static/subject/css/subject_detail.css?"))
        self.assertIn("v=", url)
