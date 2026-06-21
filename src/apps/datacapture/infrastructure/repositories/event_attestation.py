import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from django.db.models import Max, Prefetch
from django.utils import timezone

from apps.datacapture.infrastructure.persistence.models import (
    DataCaptureEventAttestation,
    DataCaptureEventAttestationPage,
    DataCapturePageEntry,
    DataCapturePageState,
)
from apps.subject.models import SubjectEventInstance


@dataclass(frozen=True)
class EventAttestationEventContext:
    event_instance_id: int
    study_id: int
    study_version: str
    site_id: int
    subject_id: int
    event_definition_id: int
    event_name: str
    event_status: str


@dataclass(frozen=True)
class EventAttestationPageScopeSnapshot:
    page_state_id: int
    page_entry_id: int | None
    crf_template_id: int
    form_name: str
    data_version: int
    page_status: str
    page_data_hash: str
    entry_updated_at: datetime | None = None


@dataclass(frozen=True)
class EventAttestationRecordSnapshot:
    id: int
    attestation_policy_id: int
    attestation_no: int
    policy_code: str
    action_kind: str
    status: str
    action_label: str
    statement_text: str
    attested_by_id: int
    signer_name: str
    attested_at: datetime | None
    scope_digest: str
    invalidation_reason_text: str
    revocation_reason: str
    supersedes_attestation_id: int | None


class DjangoEventAttestationRepository:
    def get_event_context(self, *, event_instance_id: int) -> EventAttestationEventContext | None:
        event = (
            SubjectEventInstance.objects.filter(pk=event_instance_id, deleted=False)
            .select_related("subject", "subject__site", "event_definition")
            .first()
        )
        if event is None:
            return None
        return EventAttestationEventContext(
            event_instance_id=int(event.pk),
            study_id=int(event.study_id),
            study_version=str(event.study_version or ""),
            site_id=int(event.subject.site_id),
            subject_id=int(event.subject_id),
            event_definition_id=int(event.event_definition_id),
            event_name=str(event.event_name_snapshot or event.event_definition.name or ""),
            event_status=str(event.status or ""),
        )

    def list_page_scope(self, *, event_instance_id: int) -> list[EventAttestationPageScopeSnapshot]:
        submitted_entries = DataCapturePageEntry.objects.filter(
            deleted=False,
            status="submitted",
        ).order_by("-entry_no", "-id")
        page_states = (
            DataCapturePageState.objects.filter(visit_id=event_instance_id, deleted=False)
            .select_related("current_entry", "crf_template")
            .prefetch_related(Prefetch("page_entries", queryset=submitted_entries, to_attr="submitted_entries"))
            .order_by("event_form_binding_id", "repeat_index", "id")
        )
        snapshots: list[EventAttestationPageScopeSnapshot] = []
        for page_state in page_states:
            page_entry = self._scope_page_entry(page_state)
            snapshots.append(
                EventAttestationPageScopeSnapshot(
                    page_state_id=int(page_state.pk),
                    page_entry_id=int(page_entry.pk) if page_entry is not None else None,
                    crf_template_id=int(page_state.crf_template_id),
                    form_name=self._form_name(page_state.crf_template),
                    data_version=int(page_state.data_version or 0),
                    page_status=str(page_state.status or ""),
                    page_data_hash=self._page_data_hash(page_state=page_state, page_entry=page_entry),
                    entry_updated_at=getattr(page_entry, "updated_at", None),
                )
            )
        return snapshots

    def list_attestations_for_event(self, *, event_instance_id: int) -> list[EventAttestationRecordSnapshot]:
        rows = (
            DataCaptureEventAttestation.objects.filter(event_instance_id=event_instance_id)
            .order_by("-attested_at", "-id")
        )
        return [self._to_attestation_snapshot(row) for row in rows]

    def get_attestation(self, *, event_attestation_id: int):
        return (
            DataCaptureEventAttestation.objects.filter(pk=event_attestation_id)
            .select_related("event_instance")
            .first()
        )

    def create_attestation(
        self,
        *,
        event_context: EventAttestationEventContext,
        policy,
        page_scope: list[EventAttestationPageScopeSnapshot],
        scope_digest: str,
        actor_user_id: int,
        signer_name: str,
        language_code: str,
        confirmation_accepted: bool,
    ) -> EventAttestationRecordSnapshot:
        now = timezone.now()
        SubjectEventInstance.objects.select_for_update().filter(
            pk=event_context.event_instance_id,
        ).only("id").first()
        active_rows = DataCaptureEventAttestation.objects.select_for_update().filter(
            event_instance_id=event_context.event_instance_id,
            attestation_policy_id=policy.id,
            status=DataCaptureEventAttestation.Status.ACTIVE,
        )
        active = active_rows.order_by("-attested_at", "-id").first()
        if active is not None:
            active_rows.update(
                status=DataCaptureEventAttestation.Status.SUPERSEDED,
                updated_at=now,
                updated_by_id=actor_user_id,
            )
        max_no = (
            DataCaptureEventAttestation.objects.filter(
                event_instance_id=event_context.event_instance_id,
                attestation_policy_id=policy.id,
            ).aggregate(value=Max("attestation_no"))["value"]
            or 0
        )
        attestation = DataCaptureEventAttestation.objects.create(
            created_at=now,
            updated_at=now,
            study_id=event_context.study_id,
            site_id=event_context.site_id,
            subject_id=event_context.subject_id,
            event_instance_id=event_context.event_instance_id,
            attestation_policy_id=policy.id,
            attestation_no=int(max_no) + 1,
            study_version_snapshot=policy.study_version,
            policy_code_snapshot=policy.code,
            action_kind_snapshot=policy.action_kind,
            status=DataCaptureEventAttestation.Status.ACTIVE,
            language_code=language_code,
            statement_code_snapshot=policy.statement_code,
            statement_version_snapshot=policy.statement_version,
            dialog_title_snapshot=policy.dialog_title,
            action_label_snapshot=policy.action_label,
            statement_text_snapshot=policy.statement_text,
            confirmation_label_snapshot=policy.confirmation_label or None,
            confirmation_accepted=confirmation_accepted,
            attested_by_id=actor_user_id,
            attested_at=now,
            signer_name_snapshot=signer_name,
            signer_role_code_snapshot=policy.required_role_code or None,
            scope_digest=scope_digest,
            supersedes_attestation_id=getattr(active, "id", None),
            created_by_id=actor_user_id,
            updated_by_id=actor_user_id,
        )
        DataCaptureEventAttestationPage.objects.bulk_create(
            [
                DataCaptureEventAttestationPage(
                    event_attestation_id=attestation.pk,
                    page_state_id=page.page_state_id,
                    page_entry_id=page.page_entry_id,
                    crf_template_id=page.crf_template_id,
                    data_version=page.data_version,
                    page_status_snapshot=page.page_status,
                    page_data_hash=page.page_data_hash,
                    captured_at=now,
                )
                for page in page_scope
                if page.page_entry_id is not None
            ]
        )
        return self._to_attestation_snapshot(attestation)

    def revoke_attestation(
        self,
        *,
        attestation,
        actor_user_id: int,
        reason_text: str,
    ) -> EventAttestationRecordSnapshot:
        now = timezone.now()
        attestation.status = DataCaptureEventAttestation.Status.REVOKED
        attestation.revoked_at = now
        attestation.revoked_by_id = actor_user_id
        attestation.revocation_reason = reason_text
        attestation.updated_at = now
        attestation.updated_by_id = actor_user_id
        attestation.save(
            update_fields=[
                "status",
                "revoked_at",
                "revoked_by_id",
                "revocation_reason",
                "updated_at",
                "updated_by_id",
            ]
        )
        return self._to_attestation_snapshot(attestation)

    def invalidate_active_attestations(
        self,
        *,
        event_instance_id: int,
        change_type: str,
        actor_user_id: int | None,
        reason_text: str,
    ) -> int:
        normalized_change_type = str(change_type or "").strip().lower()
        if normalized_change_type not in {"data", "scope"}:
            return 0
        flag_name = f"attestation_policy__invalidate_on_{normalized_change_type}_change"
        now = timezone.now()
        return DataCaptureEventAttestation.objects.filter(
            event_instance_id=event_instance_id,
            status=DataCaptureEventAttestation.Status.ACTIVE,
            **{flag_name: True},
        ).update(
            status=DataCaptureEventAttestation.Status.INVALIDATED,
            invalidated_at=now,
            invalidated_by_id=actor_user_id,
            invalidation_reason_code=f"{normalized_change_type.upper()}_CHANGE",
            invalidation_reason_text=reason_text,
            updated_at=now,
            updated_by_id=actor_user_id,
        )

    @staticmethod
    def _scope_page_entry(page_state):
        current_entry = getattr(page_state, "current_entry", None)
        if current_entry is not None and str(current_entry.status or "").strip().lower() == "submitted":
            return current_entry
        submitted_entries = getattr(page_state, "submitted_entries", [])
        return submitted_entries[0] if submitted_entries else None

    @staticmethod
    def _form_name(crf_template) -> str:
        if crf_template is None:
            return ""
        if hasattr(crf_template, "safe_translation_getter"):
            return str(
                crf_template.safe_translation_getter(
                    "name",
                    default=getattr(crf_template, "code", ""),
                    any_language=True,
                )
                or ""
            )
        return str(getattr(crf_template, "name", "") or getattr(crf_template, "code", "") or "")

    @classmethod
    def _page_data_hash(cls, *, page_state, page_entry) -> str:
        payload = {
            "page_state_id": int(page_state.pk),
            "page_entry_id": int(page_entry.pk) if page_entry is not None else None,
            "data_version": int(page_state.data_version or 0),
            "page_status": str(page_state.status or ""),
            "entry_data": cls._canonical_json_value(getattr(page_entry, "data", "")),
        }
        return hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _canonical_json_value(raw_value):
        try:
            loaded = json.loads(raw_value or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            return str(raw_value or "")
        return loaded

    @staticmethod
    def _to_attestation_snapshot(row) -> EventAttestationRecordSnapshot:
        return EventAttestationRecordSnapshot(
            id=int(row.pk),
            attestation_policy_id=int(row.attestation_policy_id),
            attestation_no=int(row.attestation_no or 0),
            policy_code=str(row.policy_code_snapshot or ""),
            action_kind=str(row.action_kind_snapshot or ""),
            status=str(row.status or ""),
            action_label=str(row.action_label_snapshot or ""),
            statement_text=str(row.statement_text_snapshot or ""),
            attested_by_id=int(row.attested_by_id or 0),
            signer_name=str(row.signer_name_snapshot or ""),
            attested_at=row.attested_at,
            scope_digest=str(row.scope_digest or ""),
            invalidation_reason_text=str(row.invalidation_reason_text or ""),
            revocation_reason=str(row.revocation_reason or ""),
            supersedes_attestation_id=row.supersedes_attestation_id,
        )


__all__ = [
    "DjangoEventAttestationRepository",
    "EventAttestationEventContext",
    "EventAttestationPageScopeSnapshot",
    "EventAttestationRecordSnapshot",
]
