from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.datacapture.application.exceptions import DataCaptureValidationError
from apps.datacapture.application.services.event_attestation import DataCaptureEventAttestationService
from apps.datacapture.infrastructure.repositories import (
    EventAttestationEventContext,
    EventAttestationPageScopeSnapshot,
    EventAttestationRecordSnapshot,
)
from apps.study.public import EventAttestationPolicySnapshot


def _policy(**overrides):
    values = {
        "id": 51,
        "study_id": 1,
        "study_version": "1",
        "event_definition_id": 21,
        "code": "VISIT_REVIEW",
        "action_kind": "REVIEW_COMPLETION",
        "display_order": 1,
        "statement_code": "VISIT_REVIEW_STMT",
        "statement_version": "1",
        "required_permission_code": "SDV.MARK",
        "required_role_code": "",
        "delegation_task_code": "",
        "gate_code": "DEFAULT",
        "requires_confirmation_checkbox": True,
        "requires_signature": False,
        "requires_reauthentication": False,
        "invalidate_on_data_change": True,
        "invalidate_on_scope_change": True,
        "is_required_for_lock": False,
        "dialog_title": "Complete Visit Review",
        "action_label": "Complete Review",
        "statement_text": "I reviewed this visit.",
        "confirmation_label": "I confirm.",
        "success_message": "Review completed.",
    }
    values.update(overrides)
    return EventAttestationPolicySnapshot(**values)


class _EventAttestationRepository:
    def __init__(self):
        self.created = []
        self.history = []
        self.revoked = []
        self.context = EventAttestationEventContext(
            event_instance_id=11,
            study_id=1,
            study_version="1",
            site_id=2,
            subject_id=3,
            event_definition_id=21,
            event_name="Visit 1",
            event_status="completed",
        )
        self.page_scope = [
            EventAttestationPageScopeSnapshot(
                page_state_id=101,
                page_entry_id=201,
                crf_template_id=301,
                form_name="Vitals",
                data_version=1,
                page_status="submitted",
                page_data_hash="abc",
            )
        ]
        self.attestation_row = SimpleNamespace(
            id=91,
            event_instance_id=11,
            attestation_policy_id=51,
            status="ACTIVE",
        )

    def get_event_context(self, *, event_instance_id):
        return self.context if int(event_instance_id) == self.context.event_instance_id else None

    def list_page_scope(self, *, event_instance_id):
        return list(self.page_scope)

    def list_attestations_for_event(self, *, event_instance_id):
        return list(self.history)

    def create_attestation(self, **kwargs):
        record = EventAttestationRecordSnapshot(
            id=91,
            attestation_policy_id=kwargs["policy"].id,
            attestation_no=1,
            policy_code=kwargs["policy"].code,
            action_kind=kwargs["policy"].action_kind,
            status="ACTIVE",
            action_label=kwargs["policy"].action_label,
            statement_text=kwargs["policy"].statement_text,
            attested_by_id=kwargs["actor_user_id"],
            signer_name=kwargs["signer_name"],
            attested_at=None,
            scope_digest=kwargs["scope_digest"],
            invalidation_reason_text="",
            revocation_reason="",
            supersedes_attestation_id=None,
        )
        self.created.append(kwargs)
        self.history.append(record)
        return record

    def get_attestation(self, *, event_attestation_id):
        if int(event_attestation_id) != int(self.attestation_row.id):
            return None
        return self.attestation_row

    def revoke_attestation(self, *, attestation, actor_user_id, reason_text):
        record = EventAttestationRecordSnapshot(
            id=int(attestation.id),
            attestation_policy_id=int(attestation.attestation_policy_id),
            attestation_no=1,
            policy_code="VISIT_REVIEW",
            action_kind="REVIEW_COMPLETION",
            status="REVOKED",
            action_label="Complete Review",
            statement_text="I reviewed this visit.",
            attested_by_id=actor_user_id,
            signer_name="Reviewer",
            attested_at=None,
            scope_digest="old",
            invalidation_reason_text="",
            revocation_reason=reason_text,
            supersedes_attestation_id=None,
        )
        self.revoked.append(record)
        return record


class DataCaptureEventAttestationServiceTests(SimpleTestCase):
    def _service(self, *, policy=None, repository=None, permission_checker=None):
        return DataCaptureEventAttestationService(
            repository=repository or _EventAttestationRepository(),
            policy_reader=lambda **kwargs: [policy or _policy()],
            query_summary_reader=lambda **kwargs: {
                "blocking_open": 0,
                "validation_issues_open": 0,
                "hard_validation_issues_open": 0,
            },
            permission_checker=permission_checker or (lambda **kwargs: SimpleNamespace(is_allowed=True)),
            user_display_reader=lambda user_ids: {int(user_ids[0]): "Reviewer"},
        )

    @staticmethod
    def _without_db_atomic(callback, *args, **kwargs):
        with (
            patch("django.db.transaction.Atomic.__enter__", return_value=None),
            patch("django.db.transaction.Atomic.__exit__", return_value=None),
        ):
            return callback(*args, **kwargs)

    def test_panel_marks_policy_ready_when_scope_permission_and_queries_pass(self):
        panel = self._service().get_panel(event_instance_id=11, actor_user_id=7)

        self.assertTrue(panel["has_policies"])
        self.assertEqual(panel["summary"]["page_count"], 1)
        self.assertTrue(panel["policies"][0]["readiness"]["can_submit"])

    def test_current_certification_check_requires_active_certification_for_current_scope(self):
        repository = _EventAttestationRepository()
        repository.history.append(
            self._attestation_record(
                action_kind="CERTIFICATION",
                status="ACTIVE",
                scope_digest=DataCaptureEventAttestationService._scope_digest(repository.page_scope),
            )
        )

        self.assertTrue(
            self._service(repository=repository).has_current_active_certification(
                event_instance_id=11,
            )
        )

    def test_current_certification_check_rejects_review_or_stale_scope(self):
        repository = _EventAttestationRepository()
        current_scope_digest = DataCaptureEventAttestationService._scope_digest(repository.page_scope)
        repository.history.extend(
            [
                self._attestation_record(
                    action_kind="REVIEW_COMPLETION",
                    status="ACTIVE",
                    scope_digest=current_scope_digest,
                ),
                self._attestation_record(
                    action_kind="CERTIFICATION",
                    status="ACTIVE",
                    scope_digest="old-scope",
                ),
            ]
        )

        self.assertFalse(
            self._service(repository=repository).has_current_active_certification(
                event_instance_id=11,
            )
        )

    def test_attest_event_persists_record_when_confirmation_is_accepted(self):
        repository = _EventAttestationRepository()
        service = self._service(repository=repository)

        result = self._without_db_atomic(
            service.attest_event_for_policy,
            event_instance_id=11,
            attestation_policy_id=51,
            actor_user_id=7,
            confirmation_accepted=True,
        )

        self.assertTrue(result["ok"])
        self.assertEqual(repository.created[0]["signer_name"], "Reviewer")
        self.assertEqual(result["attestation"]["status"], "ACTIVE")

    def test_signature_policy_uses_confirmation_checkbox_until_signature_is_implemented(self):
        repository = _EventAttestationRepository()
        service = self._service(
            policy=_policy(requires_signature=True, requires_confirmation_checkbox=False),
            repository=repository,
        )

        panel = service.get_panel(event_instance_id=11, actor_user_id=7)

        self.assertTrue(panel["policies"][0]["requires_confirmation_checkbox"])
        self.assertTrue(panel["policies"][0]["readiness"]["can_submit"])
        self.assertIn("confirmation checkbox is used for now", panel["policies"][0]["readiness"]["warnings"][0])

        result = self._without_db_atomic(
            service.attest_event_for_policy,
            event_instance_id=11,
            attestation_policy_id=51,
            actor_user_id=7,
            confirmation_accepted=True,
        )

        self.assertTrue(result["ok"])
        self.assertTrue(repository.created[0]["confirmation_accepted"])

    def test_signature_policy_requires_confirmation_even_without_policy_checkbox_flag(self):
        service = self._service(policy=_policy(requires_signature=True, requires_confirmation_checkbox=False))

        with self.assertRaises(DataCaptureValidationError) as ctx:
            self._without_db_atomic(
                service.attest_event_for_policy,
                event_instance_id=11,
                attestation_policy_id=51,
                actor_user_id=7,
                confirmation_accepted=False,
            )

        self.assertIn("Confirmation is required", str(ctx.exception))

    @staticmethod
    def _attestation_record(
        *,
        action_kind: str,
        status: str,
        scope_digest: str,
    ) -> EventAttestationRecordSnapshot:
        return EventAttestationRecordSnapshot(
            id=91,
            attestation_policy_id=51,
            attestation_no=1,
            policy_code="VISIT_CERT",
            action_kind=action_kind,
            status=status,
            action_label="Certify",
            statement_text="I certify this visit.",
            attested_by_id=7,
            signer_name="Reviewer",
            attested_at=None,
            scope_digest=scope_digest,
            invalidation_reason_text="",
            revocation_reason="",
            supersedes_attestation_id=None,
        )

    def test_panel_blocks_duplicate_current_active_attestation(self):
        repository = _EventAttestationRepository()
        service = self._service(repository=repository)
        self._without_db_atomic(
            service.attest_event_for_policy,
            event_instance_id=11,
            attestation_policy_id=51,
            actor_user_id=7,
            confirmation_accepted=True,
        )

        panel = service.get_panel(event_instance_id=11, actor_user_id=7)

        self.assertFalse(panel["policies"][0]["readiness"]["can_submit"])
        self.assertIn("Current attestation is already active", panel["policies"][0]["readiness"]["blockers"][0])

    def test_soft_validation_issues_warn_but_do_not_block_attestation(self):
        service = DataCaptureEventAttestationService(
            repository=_EventAttestationRepository(),
            policy_reader=lambda **kwargs: [_policy()],
            query_summary_reader=lambda **kwargs: {
                "blocking_open": 0,
                "validation_issues_open": 1,
                "hard_validation_issues_open": 0,
            },
            permission_checker=lambda **kwargs: SimpleNamespace(is_allowed=True),
            user_display_reader=lambda user_ids: {int(user_ids[0]): "Reviewer"},
        )

        panel = service.get_panel(event_instance_id=11, actor_user_id=7)

        self.assertTrue(panel["policies"][0]["readiness"]["can_submit"])
        self.assertIn("non-HARD validation issues", panel["policies"][0]["readiness"]["warnings"][0])

    def test_hard_validation_issues_block_attestation(self):
        service = DataCaptureEventAttestationService(
            repository=_EventAttestationRepository(),
            policy_reader=lambda **kwargs: [_policy()],
            query_summary_reader=lambda **kwargs: {
                "blocking_open": 0,
                "validation_issues_open": 1,
                "hard_validation_issues_open": 1,
            },
            permission_checker=lambda **kwargs: SimpleNamespace(is_allowed=True),
            user_display_reader=lambda user_ids: {int(user_ids[0]): "Reviewer"},
        )

        panel = service.get_panel(event_instance_id=11, actor_user_id=7)

        self.assertFalse(panel["policies"][0]["readiness"]["can_submit"])
        self.assertIn("HARD validation issues", panel["policies"][0]["readiness"]["blockers"][0])

    def test_revoke_uses_independent_revoke_permission(self):
        repository = _EventAttestationRepository()
        seen_permission_codes = []

        def permission_checker(**kwargs):
            seen_permission_codes.append(kwargs["permission_code"])
            return SimpleNamespace(is_allowed=kwargs["permission_code"] == "EVENT_ATTESTATION.REVOKE")

        service = self._service(repository=repository, permission_checker=permission_checker)

        result = self._without_db_atomic(
            service.revoke_event_attestation,
            event_attestation_id=91,
            actor_user_id=7,
            reason_text="Incorrect attestation.",
        )

        self.assertTrue(result["ok"])
        self.assertEqual(seen_permission_codes, ["EVENT_ATTESTATION.REVOKE"])
        self.assertEqual(repository.revoked[0].revocation_reason, "Incorrect attestation.")
