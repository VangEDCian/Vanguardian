import hashlib
import json
from dataclasses import asdict
from datetime import datetime

from django.db import transaction

from apps.datacapture.application.exceptions import DataCaptureValidationError
from apps.datacapture.infrastructure.repositories import (
    DjangoEventAttestationRepository,
    EventAttestationEventContext,
    EventAttestationPageScopeSnapshot,
    EventAttestationRecordSnapshot,
)
from apps.identity.public import ResourceContext, can_perform, get_user_display_map
from apps.reconcile.public import summarize_reconcile_workbench_for_page_states
from apps.study.public import EventAttestationPolicySnapshot, list_event_attestation_policies_for_event


class DataCaptureEventAttestationService:
    REVOKE_PERMISSION_CODE = "EVENT_ATTESTATION.REVOKE"
    CERTIFICATION_ACTION_KIND = "CERTIFICATION"
    REVIEW_READY_STATUSES = frozenset(
        {
            "submitted",
            "under_review",
            "verified",
            "finalized",
            "locked",
        }
    )

    def __init__(
        self,
        *,
        repository=None,
        policy_reader=None,
        query_summary_reader=None,
        permission_checker=None,
        user_display_reader=None,
        subject_event_lifecycle_adapter=None,
    ):
        self.repository = repository or DjangoEventAttestationRepository()
        self.policy_reader = policy_reader or list_event_attestation_policies_for_event
        self.query_summary_reader = query_summary_reader or summarize_reconcile_workbench_for_page_states
        self.permission_checker = permission_checker or can_perform
        self.user_display_reader = user_display_reader or get_user_display_map
        self.subject_event_lifecycle_adapter = subject_event_lifecycle_adapter

    def get_panel(
        self,
        *,
        event_instance_id: int,
        actor_user_id: int | None = None,
        actor_is_superuser: bool = False,
        language_code: str | None = None,
    ) -> dict:
        event_context = self._event_context_or_raise(event_instance_id)
        policies = self._policies(event_context=event_context, language_code=language_code)
        if not policies:
            return {"has_policies": False, "policies": [], "history": [], "summary": {}}
        page_scope = self.repository.list_page_scope(event_instance_id=event_instance_id)
        query_summary = self.query_summary_reader(
            page_state_ids=tuple(page.page_state_id for page in page_scope)
        )
        scope_digest = self._scope_digest(page_scope)
        history = self.repository.list_attestations_for_event(event_instance_id=event_instance_id)
        active_by_policy_id = {
            int(row.attestation_policy_id): row
            for row in history
            if str(row.status or "").upper() == "ACTIVE"
        }
        return {
            "has_policies": True,
            "event_instance_id": event_context.event_instance_id,
            "event_name": event_context.event_name,
            "scope_digest": scope_digest,
            "summary": {
                "page_count": len(page_scope),
                "submitted_page_count": sum(1 for page in page_scope if page.page_entry_id is not None),
                "blocking_query_count": int(query_summary.get("blocking_open", 0) or 0),
                "validation_issue_count": int(query_summary.get("validation_issues_open", 0) or 0),
            },
            "policies": [
                self._policy_panel_item(
                    event_context=event_context,
                    policy=policy,
                    page_scope=page_scope,
                    query_summary=query_summary,
                    scope_digest=scope_digest,
                    active_attestation=active_by_policy_id.get(int(policy.id)),
                    actor_user_id=actor_user_id,
                    actor_is_superuser=actor_is_superuser,
                )
                for policy in policies
            ],
            "history": [self._record_payload(row, current_scope_digest=scope_digest) for row in history],
        }

    @transaction.atomic
    def attest_event_for_policy(
        self,
        *,
        event_instance_id: int,
        attestation_policy_id: int,
        actor_user_id: int,
        actor_is_superuser: bool = False,
        language_code: str | None = None,
        confirmation_accepted: bool = False,
        expected_study_id: int | None = None,
        expected_subject_id: int | None = None,
    ) -> dict:
        event_context = self._event_context_or_raise(event_instance_id)
        self._validate_url_scope(
            event_context=event_context,
            expected_study_id=expected_study_id,
            expected_subject_id=expected_subject_id,
        )
        policy = self._policy_or_raise(
            event_context=event_context,
            attestation_policy_id=attestation_policy_id,
            language_code=language_code,
        )
        if self._requires_confirmation(policy) and not confirmation_accepted:
            raise DataCaptureValidationError("Confirmation is required before attestation.")
        page_scope = self.repository.list_page_scope(event_instance_id=event_instance_id)
        query_summary = self.query_summary_reader(
            page_state_ids=tuple(page.page_state_id for page in page_scope)
        )
        scope_digest = self._scope_digest(page_scope)
        history = self.repository.list_attestations_for_event(event_instance_id=event_instance_id)
        active_attestation = next(
            (
                row
                for row in history
                if int(row.attestation_policy_id) == int(policy.id)
                and str(row.status or "").upper() == "ACTIVE"
            ),
            None,
        )
        readiness = self._readiness(
            event_context=event_context,
            policy=policy,
            page_scope=page_scope,
            query_summary=query_summary,
            scope_digest=scope_digest,
            active_attestation=active_attestation,
            actor_user_id=actor_user_id,
            actor_is_superuser=actor_is_superuser,
        )
        if not readiness["can_submit"]:
            raise DataCaptureValidationError("; ".join(readiness["blockers"]) or "Attestation is not ready.")
        signer_name = self._signer_name(actor_user_id)
        record = self.repository.create_attestation(
            event_context=event_context,
            policy=policy,
            page_scope=page_scope,
            scope_digest=scope_digest,
            actor_user_id=actor_user_id,
            signer_name=signer_name,
            language_code=self._normalize_language(language_code),
            confirmation_accepted=confirmation_accepted or not self._requires_confirmation(policy),
        )
        self._trigger_transition_after_certification(
            event_context=event_context,
            policy=policy,
            actor_user_id=actor_user_id,
        )
        return {"ok": True, "attestation": self._record_payload(record, current_scope_digest=scope_digest)}

    @transaction.atomic
    def revoke_event_attestation(
        self,
        *,
        event_attestation_id: int,
        actor_user_id: int,
        actor_is_superuser: bool = False,
        reason_text: str,
        expected_study_id: int | None = None,
        expected_subject_id: int | None = None,
    ) -> dict:
        normalized_reason = str(reason_text or "").strip()
        if not normalized_reason:
            raise DataCaptureValidationError("Revocation reason is required.")
        attestation = self.repository.get_attestation(event_attestation_id=event_attestation_id)
        if attestation is None:
            raise DataCaptureValidationError("Attestation not found.")
        event_context = self._event_context_or_raise(int(attestation.event_instance_id))
        self._validate_url_scope(
            event_context=event_context,
            expected_study_id=expected_study_id,
            expected_subject_id=expected_subject_id,
        )
        self._require_revoke_permission(
            event_context=event_context,
            actor_user_id=actor_user_id,
            actor_is_superuser=actor_is_superuser,
        )
        if str(attestation.status or "").upper() != "ACTIVE":
            raise DataCaptureValidationError("Only active attestations can be revoked.")
        record = self.repository.revoke_attestation(
            attestation=attestation,
            actor_user_id=actor_user_id,
            reason_text=normalized_reason,
        )
        current_scope_digest = self._scope_digest(
            self.repository.list_page_scope(event_instance_id=event_context.event_instance_id)
        )
        return {"ok": True, "attestation": self._record_payload(record, current_scope_digest=current_scope_digest)}

    def invalidate_active_attestations_for_event(
        self,
        *,
        event_instance_id: int,
        change_type: str,
        actor_user_id: int | None = None,
        reason_text: str = "",
    ) -> int:
        return self.repository.invalidate_active_attestations(
            event_instance_id=event_instance_id,
            change_type=change_type,
            actor_user_id=actor_user_id,
            reason_text=reason_text or f"Event attestation invalidated by {change_type} change.",
        )

    def has_current_active_certification(self, *, event_instance_id: int) -> bool:
        page_scope = self.repository.list_page_scope(event_instance_id=event_instance_id)
        current_scope_digest = self._scope_digest(page_scope)
        for row in self.repository.list_attestations_for_event(event_instance_id=event_instance_id):
            if str(row.status or "").strip().upper() != "ACTIVE":
                continue
            if str(row.action_kind or "").strip().upper() != self.CERTIFICATION_ACTION_KIND:
                continue
            if str(row.scope_digest or "") != current_scope_digest:
                continue
            return True
        return False

    def _trigger_transition_after_certification(
        self,
        *,
        event_context: EventAttestationEventContext,
        policy: EventAttestationPolicySnapshot,
        actor_user_id: int,
    ) -> None:
        if str(policy.action_kind or "").strip().upper() != self.CERTIFICATION_ACTION_KIND:
            return
        adapter = self.subject_event_lifecycle_adapter
        if adapter is None:
            from apps.subject.public import SubjectEventLifecycleAdapter

            adapter = SubjectEventLifecycleAdapter()
        adapter.trigger_event_transition(
            source_event_instance_id=event_context.event_instance_id,
            facts=self._certification_transition_facts(event_context=event_context),
            actor_user_id=actor_user_id,
            trigger_source="datacapture_event_certification",
        )

    @staticmethod
    def _certification_transition_facts(*, event_context: EventAttestationEventContext) -> dict[str, bool]:
        event_code = str(event_context.event_code or "").strip().lower()
        facts = {"source_event.certified": True}
        if event_code:
            facts[f"{event_code}.event_certified"] = True
        return facts

    def _event_context_or_raise(self, event_instance_id: int) -> EventAttestationEventContext:
        event_context = self.repository.get_event_context(event_instance_id=event_instance_id)
        if event_context is None:
            raise DataCaptureValidationError("Event instance not found.")
        return event_context

    def _policies(
        self,
        *,
        event_context: EventAttestationEventContext,
        language_code: str | None,
    ) -> list[EventAttestationPolicySnapshot]:
        return self.policy_reader(
            study_id=event_context.study_id,
            study_version=event_context.study_version,
            event_definition_id=event_context.event_definition_id,
            language_code=language_code,
        )

    def _policy_or_raise(
        self,
        *,
        event_context: EventAttestationEventContext,
        attestation_policy_id: int,
        language_code: str | None,
    ) -> EventAttestationPolicySnapshot:
        for policy in self._policies(event_context=event_context, language_code=language_code):
            if int(policy.id) == int(attestation_policy_id):
                return policy
        raise DataCaptureValidationError("Attestation policy not found or disabled.")

    def _policy_panel_item(
        self,
        *,
        event_context: EventAttestationEventContext,
        policy: EventAttestationPolicySnapshot,
        page_scope: list[EventAttestationPageScopeSnapshot],
        query_summary: dict[str, int],
        scope_digest: str,
        active_attestation: EventAttestationRecordSnapshot | None,
        actor_user_id: int | None,
        actor_is_superuser: bool,
    ) -> dict:
        readiness = self._readiness(
            event_context=event_context,
            policy=policy,
            page_scope=page_scope,
            query_summary=query_summary,
            scope_digest=scope_digest,
            active_attestation=active_attestation,
            actor_user_id=actor_user_id,
            actor_is_superuser=actor_is_superuser,
        )
        return {
            "policy_id": policy.id,
            "code": policy.code,
            "action_kind": policy.action_kind,
            "dialog_title": policy.dialog_title,
            "action_label": policy.action_label,
            "statement_text": policy.statement_text,
            "confirmation_label": policy.confirmation_label,
            "success_message": policy.success_message or f"{policy.action_label} completed.",
            "requires_confirmation_checkbox": self._requires_confirmation(policy),
            "requires_signature": policy.requires_signature,
            "requires_reauthentication": policy.requires_reauthentication,
            "active_attestation": (
                self._record_payload(active_attestation, current_scope_digest=scope_digest)
                if active_attestation is not None
                else None
            ),
            "readiness": readiness,
        }

    def _readiness(
        self,
        *,
        event_context: EventAttestationEventContext,
        policy: EventAttestationPolicySnapshot,
        page_scope: list[EventAttestationPageScopeSnapshot],
        query_summary: dict[str, int],
        scope_digest: str,
        active_attestation: EventAttestationRecordSnapshot | None,
        actor_user_id: int | None,
        actor_is_superuser: bool,
    ) -> dict:
        blockers: list[str] = []
        warnings: list[str] = []
        if not page_scope:
            blockers.append("No submitted page scope is available for this event.")
        missing_entries = [page.form_name or str(page.page_state_id) for page in page_scope if page.page_entry_id is None]
        if missing_entries:
            blockers.append("All event pages must have submitted data before attestation.")
        not_ready_pages = [
            page.form_name or str(page.page_state_id)
            for page in page_scope
            if str(page.page_status or "").strip().lower() not in self.REVIEW_READY_STATUSES
        ]
        if not_ready_pages:
            blockers.append("All event pages must be submitted or in review-ready status.")
        if int(query_summary.get("blocking_open", 0) or 0) > 0:
            blockers.append("Blocking queries must be resolved before attestation.")
        hard_validation_issue_count = int(query_summary.get("hard_validation_issues_open", 0) or 0)
        validation_issue_count = int(query_summary.get("validation_issues_open", 0) or 0)
        if hard_validation_issue_count > 0:
            blockers.append("Open HARD validation issues must be acknowledged or corrected before attestation.")
        elif validation_issue_count > 0:
            warnings.append("Open non-HARD validation issues exist; they do not block attestation.")
        if active_attestation is not None and str(active_attestation.scope_digest or "") == scope_digest:
            blockers.append("Current attestation is already active for this policy.")
        if policy.requires_reauthentication or policy.requires_signature:
            warnings.append(
                "Electronic signature or re-authentication is marked as future work; "
                "confirmation checkbox is used for now."
            )
        permission_result = self._permission_result(
            event_context=event_context,
            policy=policy,
            actor_user_id=actor_user_id,
            actor_is_superuser=actor_is_superuser,
        )
        if not permission_result["allowed"]:
            blockers.append(permission_result["message"])
        unsupported_gate_codes = {
            "",
            "NONE",
            "DEFAULT",
            "EVENT_REVIEW_READY",
            "ALL_PAGES_SUBMITTED",
            "NO_BLOCKING_QUERIES",
            "SUBMITTED_OR_VERIFIED_NO_BLOCKING_QUERIES",
        }
        gate_code = str(policy.gate_code or "").strip().upper()
        if gate_code not in unsupported_gate_codes:
            warnings.append(f"Gate {gate_code} used default readiness checks; confirm final gate semantics.")
        if active_attestation is not None and str(active_attestation.scope_digest or "") != scope_digest:
            warnings.append("Current event scope differs from the active attestation.")
        return {
            "can_submit": not blockers,
            "blockers": blockers,
            "warnings": warnings,
            "permission_allowed": permission_result["allowed"],
        }

    def _permission_result(
        self,
        *,
        event_context: EventAttestationEventContext,
        policy: EventAttestationPolicySnapshot,
        actor_user_id: int | None,
        actor_is_superuser: bool,
    ) -> dict:
        permission_code = str(policy.required_permission_code or "").strip()
        if not permission_code:
            return {"allowed": False, "message": "Policy permission code is missing."}
        return self._permission_result_for_code(
            event_context=event_context,
            permission_code=permission_code,
            actor_user_id=actor_user_id,
            actor_is_superuser=actor_is_superuser,
        )

    def _require_revoke_permission(
        self,
        *,
        event_context: EventAttestationEventContext,
        actor_user_id: int,
        actor_is_superuser: bool,
    ) -> None:
        permission_result = self._permission_result_for_code(
            event_context=event_context,
            permission_code=self.REVOKE_PERMISSION_CODE,
            actor_user_id=actor_user_id,
            actor_is_superuser=actor_is_superuser,
        )
        if not permission_result["allowed"]:
            raise DataCaptureValidationError(permission_result["message"])

    def _permission_result_for_code(
        self,
        *,
        event_context: EventAttestationEventContext,
        permission_code: str,
        actor_user_id: int | None,
        actor_is_superuser: bool,
    ) -> dict:
        if actor_is_superuser:
            return {"allowed": True, "message": ""}
        if actor_user_id is None:
            return {"allowed": False, "message": "Authenticated user is required."}
        normalized_permission_code = str(permission_code or "").strip()
        if not normalized_permission_code:
            return {"allowed": False, "message": "Permission code is missing."}
        decision = self.permission_checker(
            user_id=actor_user_id,
            permission_code=normalized_permission_code,
            resource_context=ResourceContext(
                study_id=event_context.study_id,
                study_site_id=event_context.site_id,
                subject_id=event_context.subject_id,
                visit_instance_id=event_context.event_instance_id,
            ),
        )
        if getattr(decision, "is_allowed", False):
            return {"allowed": True, "message": ""}
        return {
            "allowed": False,
            "message": getattr(decision, "deny_reason_message", "") or "Permission denied.",
        }

    def _signer_name(self, actor_user_id: int) -> str:
        display_map = self.user_display_reader([actor_user_id])
        return display_map.get(int(actor_user_id)) or str(actor_user_id)

    @staticmethod
    def _requires_confirmation(policy: EventAttestationPolicySnapshot) -> bool:
        return bool(
            policy.requires_confirmation_checkbox
            or policy.requires_signature
            or policy.requires_reauthentication
        )

    @staticmethod
    def _scope_digest(page_scope: list[EventAttestationPageScopeSnapshot]) -> str:
        payload = [
            {
                "page_state_id": page.page_state_id,
                "page_entry_id": page.page_entry_id,
                "crf_template_id": page.crf_template_id,
                "data_version": page.data_version,
                "page_status": page.page_status,
                "page_data_hash": page.page_data_hash,
            }
            for page in page_scope
        ]
        return hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _normalize_language(language_code: str | None) -> str:
        raw = str(language_code or "").strip().lower()
        return (raw.split("-", maxsplit=1)[0] if raw else "en")

    @staticmethod
    def _validate_url_scope(
        *,
        event_context: EventAttestationEventContext,
        expected_study_id: int | None,
        expected_subject_id: int | None,
    ) -> None:
        if expected_study_id is not None and int(expected_study_id) != int(event_context.study_id):
            raise DataCaptureValidationError("Event instance does not belong to the requested study.")
        if expected_subject_id is not None and int(expected_subject_id) != int(event_context.subject_id):
            raise DataCaptureValidationError("Event instance does not belong to the requested subject.")

    @staticmethod
    def _record_payload(
        record: EventAttestationRecordSnapshot | None,
        *,
        current_scope_digest: str,
    ) -> dict | None:
        if record is None:
            return None
        payload = asdict(record)
        attested_at = payload.get("attested_at")
        if isinstance(attested_at, datetime):
            payload["attested_at"] = attested_at.isoformat()
        payload["is_current_scope"] = str(record.scope_digest or "") == str(current_scope_digest or "")
        return payload


__all__ = ["DataCaptureEventAttestationService"]
