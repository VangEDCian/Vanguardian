import ast
import sys
from pathlib import Path
from unittest import TestCase

TOOLS_DIR = Path(__file__).resolve().parents[2] / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from flake8_ddd import DDDChecker  # noqa: E402


class DDDCheckerTests(TestCase):
    def _messages_for(self, source, filename):
        tree = ast.parse(source)
        return [message for *_position, message, _checker in DDDChecker(tree, filename).run()]

    def test_presentation_cannot_import_same_app_infrastructure_model(self):
        messages = self._messages_for(
            "from apps.identity.models import User\n",
            "/repo/server/src/apps/identity/presentation/web/views/users.py",
        )

        self.assertTrue(any(message.startswith("DDD001") for message in messages))

    def test_presentation_command_import_requires_mapper(self):
        messages = self._messages_for(
            "from apps.identity.application import CreateIdentityUserCommand\n",
            "/repo/server/src/apps/identity/presentation/web/views/users.py",
        )

        self.assertTrue(any(message.startswith("DDD020") for message in messages))

    def test_mapper_may_import_application_command_for_conversion(self):
        messages = self._messages_for(
            "from apps.identity.application import CreateIdentityUserCommand\n",
            "/repo/server/src/apps/identity/presentation/web/mappers/user.py",
        )

        self.assertEqual(messages, [])

    def test_public_can_import_application_but_not_infrastructure(self):
        allowed_messages = self._messages_for(
            "from apps.identity.application import CreateIdentityUserService\n",
            "/repo/server/src/apps/identity/public.py",
        )
        denied_messages = self._messages_for(
            "from apps.identity.models import User\n",
            "/repo/server/src/apps/identity/public.py",
        )

        self.assertEqual(allowed_messages, [])
        self.assertTrue(any(message.startswith("DDD001") for message in denied_messages))
