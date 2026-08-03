from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.datacapture.application.exceptions import DataCaptureValidationError
from apps.datacapture.application.services.page_lifecycle_policy import (
    DataCapturePageLifecyclePolicyService,
)


class DataCapturePageLifecyclePolicyServiceTests(SimpleTestCase):
    def test_requires_configured_next_step(self):
        service = DataCapturePageLifecyclePolicyService(
            action_state_reader=lambda **_kwargs: SimpleNamespace(
                next_step_code="CERTIFY",
                next_step=SimpleNamespace(allowed_role_ids=(12,)),
            ),
            role_checker=lambda **_kwargs: True,
        )

        with self.assertRaisesMessage(DataCaptureValidationError, "requires CERTIFY before FINALIZE"):
            service.require_step(
                snapshot=SimpleNamespace(study_id=1, site_id=2, status="verified"),
                step_code="FINALIZE",
                actor_user_id=3,
            )

    def test_requires_actor_to_have_an_allowed_role(self):
        role_check_calls = []
        service = DataCapturePageLifecyclePolicyService(
            action_state_reader=lambda **_kwargs: SimpleNamespace(
                next_step_code="CERTIFY",
                next_step=SimpleNamespace(allowed_role_ids=(12,)),
            ),
            role_checker=lambda **kwargs: role_check_calls.append(kwargs) or False,
        )

        with self.assertRaisesMessage(DataCaptureValidationError, "role is not allowed"):
            service.require_step(
                snapshot=SimpleNamespace(study_id=1, site_id=2, status="verified"),
                step_code="CERTIFY",
                actor_user_id=3,
            )

        self.assertEqual(
            role_check_calls,
            [{"user_id": 3, "study_id": 1, "site_id": 2, "role_ids": (12,)}],
        )
