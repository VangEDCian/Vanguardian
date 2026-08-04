from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.study.application.services.crf_page_lifecycle import (
    LEGACY_CRF_PAGE_LIFECYCLE,
    StudyCrfPageLifecycleService,
)
from apps.study.domain.crf_page_lifecycle import (
    CrfPageLifecycleConfigurationError,
    CrfPageLifecycleStep,
    CrfPageLifecycleStepPolicy,
    validate_crf_page_lifecycle_steps,
)


class _LifecycleRepository:
    def __init__(self, rows=(), *, configured=False):
        self.rows = list(rows)
        self.configured = configured
        self.replace_call = None

    def is_configured(self, **_kwargs):
        return self.configured

    def list_steps(self, **_kwargs):
        return list(self.rows)

    def replace_steps(self, **kwargs):
        self.replace_call = kwargs
        return list(kwargs["steps"])


ROLE_OPTIONS = [
    {
        "id": 11,
        "name": "Monitor",
        "scope_level": "STUDY_SITE",
        "permission_codes": ("SDV.MARK",),
    },
    {
        "id": 13,
        "name": "Data Manager",
        "scope_level": "STUDY",
        "permission_codes": ("DATA.LOCK",),
    },
]


class StudyCrfPageLifecycleServiceTests(SimpleTestCase):
    def test_missing_configuration_preserves_legacy_workflow(self):
        service = StudyCrfPageLifecycleService(
            repository=_LifecycleRepository(),
            role_option_reader=lambda **_kwargs: ROLE_OPTIONS,
        )

        self.assertEqual(service.list_steps(study_id=1), LEGACY_CRF_PAGE_LIFECYCLE)
        self.assertEqual(
            service.action_state(study_id=1, page_status="submitted").next_step_code,
            CrfPageLifecycleStep.VERIFY,
        )
        self.assertEqual(
            service.action_state(study_id=1, page_status="verified").next_step_code,
            CrfPageLifecycleStep.FINALIZE,
        )

    def test_configured_order_drives_next_step(self):
        repository = _LifecycleRepository(
            rows=(
                SimpleNamespace(step_code="VERIFY", display_order=1, allowed_role_ids=[11]),
                SimpleNamespace(step_code="FINALIZE", display_order=2, allowed_role_ids=[11]),
                SimpleNamespace(step_code="LOCK", display_order=4, allowed_role_ids=[13]),
            ),
            configured=True,
        )
        service = StudyCrfPageLifecycleService(
            repository=repository,
            role_option_reader=lambda **_kwargs: ROLE_OPTIONS,
        )

        self.assertEqual(
            service.action_state(study_id=1, page_status="finalized").next_step_code,
            CrfPageLifecycleStep.LOCK,
        )

    def test_legacy_certified_status_is_treated_as_verified(self):
        service = StudyCrfPageLifecycleService(
            repository=_LifecycleRepository(
                rows=(
                    SimpleNamespace(step_code="VERIFY", display_order=1, allowed_role_ids=[11]),
                    SimpleNamespace(step_code="FINALIZE", display_order=2, allowed_role_ids=[11]),
                    SimpleNamespace(step_code="LOCK", display_order=3, allowed_role_ids=[13]),
                ),
                configured=True,
            ),
            role_option_reader=lambda **_kwargs: ROLE_OPTIONS,
        )

        self.assertEqual(
            service.action_state(study_id=1, page_status="certified").next_step_code,
            CrfPageLifecycleStep.FINALIZE,
        )

    def test_explicit_empty_configuration_has_no_post_submit_step(self):
        service = StudyCrfPageLifecycleService(
            repository=_LifecycleRepository(configured=True),
            role_option_reader=lambda **_kwargs: ROLE_OPTIONS,
        )

        self.assertEqual(service.list_steps(study_id=1), ())
        self.assertIsNone(
            service.action_state(study_id=1, page_status="submitted").next_step_code
        )

    def test_page_certify_is_no_longer_a_supported_step(self):
        service = StudyCrfPageLifecycleService(
            repository=_LifecycleRepository(),
            role_option_reader=lambda **_kwargs: ROLE_OPTIONS,
        )

        with self.assertRaisesMessage(
            CrfPageLifecycleConfigurationError,
            "Unsupported CRF Page lifecycle step: CERTIFY",
        ):
            service.save(
                study_id=1,
                actor_user_id=99,
                raw_steps=[
                    {
                        "step_code": "CERTIFY",
                        "enabled": True,
                        "display_order": 1,
                        "role_ids": [11],
                    }
                ],
            )

    def test_save_persists_enabled_steps_in_requested_order(self):
        repository = _LifecycleRepository()
        service = StudyCrfPageLifecycleService(
            repository=repository,
            role_option_reader=lambda **_kwargs: ROLE_OPTIONS,
        )

        result = service.save(
            study_id=1,
            actor_user_id=99,
            raw_steps=[
                {"step_code": "VERIFY", "enabled": True, "display_order": 1, "role_ids": [11]},
                {"step_code": "FINALIZE", "enabled": False, "display_order": 2, "role_ids": []},
                {"step_code": "LOCK", "enabled": True, "display_order": 3, "role_ids": [13]},
            ],
        )

        self.assertEqual([step.step_code for step in result], ["VERIFY", "LOCK"])
        self.assertEqual(repository.replace_call["study_id"], 1)
        self.assertEqual(repository.replace_call["actor_user_id"], 99)


class CrfPageLifecycleDomainTests(SimpleTestCase):
    def test_verify_must_be_first(self):
        with self.assertRaisesMessage(
            CrfPageLifecycleConfigurationError,
            "Verify must be the first enabled step",
        ):
            validate_crf_page_lifecycle_steps(
                (
                    CrfPageLifecycleStepPolicy("FINALIZE", 1, (11,)),
                    CrfPageLifecycleStepPolicy("VERIFY", 2, (11,)),
                )
            )

    def test_lock_must_be_last(self):
        with self.assertRaisesMessage(
            CrfPageLifecycleConfigurationError,
            "Lock Page must be the last enabled step",
        ):
            validate_crf_page_lifecycle_steps(
                (
                    CrfPageLifecycleStepPolicy("LOCK", 1, (13,)),
                    CrfPageLifecycleStepPolicy("FINALIZE", 2, (11,)),
                )
            )
