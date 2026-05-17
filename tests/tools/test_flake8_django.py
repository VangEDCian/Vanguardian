import ast
import sys
from pathlib import Path
from unittest import TestCase

TOOLS_DIR = Path(__file__).resolve().parents[2] / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from flake8_django import DjangoChecker  # noqa: E402


class DjangoCheckerTests(TestCase):
    def _messages_for(self, source, filename):
        tree = ast.parse(source)
        return [message for *_position, message, _checker in DjangoChecker(tree, filename).run()]

    def test_django_index_name_cannot_exceed_30_characters(self):
        messages = self._messages_for(
            'from django.db import models\nmodels.Index(fields=["master"], name="crf_fielddefinition_translation_master_idx")\n',
            "/repo/server/src/apps/crf/infrastructure/persistence/models/crf.py",
        )

        self.assertTrue(any(message.startswith("DJG030") for message in messages))

    def test_django_index_name_allows_30_characters(self):
        messages = self._messages_for(
            'from django.db import models\nmodels.Index(fields=["master"], name="a23456789012345678901234567890")\n',
            "/repo/server/src/apps/crf/infrastructure/persistence/models/crf.py",
        )

        self.assertFalse(any(message.startswith("DJG030") for message in messages))

    def test_non_index_calls_are_ignored(self):
        messages = self._messages_for(
            'from django.db import models\nmodels.UniqueConstraint(fields=["code"], name="very_long_constraint_name_that_is_not_an_index")\n',
            "/repo/server/src/apps/crf/infrastructure/persistence/models/crf.py",
        )

        self.assertEqual(messages, [])
