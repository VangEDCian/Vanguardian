from dataclasses import dataclass

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.datacapture.application.commands import SavePageCommand, SubmitPageCommand
from apps.datacapture.domain.exceptions import (
    InvalidPagePayloadError,
    PageNotEditableError,
    UnsupportedEntryStatusError,
)
from apps.datacapture.domain.services.page_capture_save_submit import (
    build_submit_execution_plan,
    resolve_save_draft_execution_plan,
)
from apps.datacapture.infrastructure.repositories import DjangoDataCapturePageRepository


@dataclass(frozen=True)
class SavePageResult:
    entry_id: int | None
    entry_status: str
    page_status: str | None
    needs_confirmation: bool = False


@dataclass(frozen=True)
class SubmitPageResult:
    entry_id: int | None
    entry_status: str
    page_status: str


def _raise_as_http(exc: PageNotEditableError | InvalidPagePayloadError | UnsupportedEntryStatusError) -> None:
    if isinstance(exc, PageNotEditableError):
        raise PermissionDenied("Page is not editable") from exc
    raise ValidationError([str(exc)]) from exc


class DataCaptureSaveSubmitPageService:

    repository_class = DjangoDataCapturePageRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def _upsert_draft_page_state(self, command: SavePageCommand) -> None:
        self.repository.upsert_page_state(
            subject_id=command.subject_id,
            visit_id=command.visit_id,
            crf_template_id=command.crf_template_id,
            data=command.data,
            status="draft",
            actor_user_id=command.actor_user_id,
        )

    @transaction.atomic
    def save(self, command: SavePageCommand) -> SavePageResult:
        page_state = self.repository.get_page_state_by_scope(
            subject_id=command.subject_id,
            visit_id=command.visit_id,
            crf_template_id=command.crf_template_id,
        )
        latest = self.repository.get_current_entry(
            subject_id=command.subject_id,
            visit_id=command.visit_id,
            crf_template_id=command.crf_template_id,
        )
        try:
            plan = resolve_save_draft_execution_plan(
                page_state=page_state,
                latest=latest,
                payload=command.data,
            )
        except PageNotEditableError as exc:
            _raise_as_http(exc)
        except (InvalidPagePayloadError, UnsupportedEntryStatusError) as exc:
            _raise_as_http(exc)

        if plan.branch == "noop_identical_submitted":
            assert latest is not None
            return SavePageResult(
                entry_id=latest.id,
                entry_status=latest.status,
                page_status=plan.noop_page_status,
                needs_confirmation=False,
            )

        if plan.branch == "create_initial":
            entry = self.repository.create_initial_entry(
                subject_id=command.subject_id,
                visit_id=command.visit_id,
                crf_template_id=command.crf_template_id,
                data=command.data,
                actor_user_id=command.actor_user_id,
            )
            self._upsert_draft_page_state(command)
            return SavePageResult(
                entry_id=entry.pk,
                entry_status=entry.status,
                page_status="draft",
                needs_confirmation=False,
            )

        if plan.branch == "update_draft":
            refreshed = self.repository.update_latest_draft_entry_data(
                subject_id=command.subject_id,
                visit_id=command.visit_id,
                crf_template_id=command.crf_template_id,
                data=command.data,
                actor_user_id=command.actor_user_id,
            )
            snapshot = refreshed or latest
            assert snapshot is not None
            self._upsert_draft_page_state(command)
            return SavePageResult(
                entry_id=snapshot.id,
                entry_status=snapshot.status,
                page_status="draft",
                needs_confirmation=False,
            )

        if plan.branch == "correction_from_submitted":
            entry = self.repository.create_correction_draft_from_submitted_entry(
                subject_id=command.subject_id,
                visit_id=command.visit_id,
                crf_template_id=command.crf_template_id,
                data=command.data,
                actor_user_id=command.actor_user_id,
            )
            self._upsert_draft_page_state(command)
            return SavePageResult(
                entry_id=entry.pk,
                entry_status=entry.status,
                page_status="draft",
                needs_confirmation=True,
            )

        raise RuntimeError(f"Unhandled save draft branch: {plan.branch!r}")

    @transaction.atomic
    def submit(self, command: SubmitPageCommand) -> SubmitPageResult:
        page_state = self.repository.get_page_state_by_scope(
            subject_id=command.subject_id,
            visit_id=command.visit_id,
            crf_template_id=command.crf_template_id,
        )
        latest = self.repository.get_current_entry(
            subject_id=command.subject_id,
            visit_id=command.visit_id,
            crf_template_id=command.crf_template_id,
        )
        has_other = False
        if latest is not None and latest.status == "draft":
            has_other = self.repository.has_other_submitted_entry(
                subject_id=command.subject_id,
                visit_id=command.visit_id,
                crf_template_id=command.crf_template_id,
                exclude_entry_id=latest.id,
            )
        try:
            plan = build_submit_execution_plan(
                page_state=page_state,
                latest=latest,
                has_other_submitted_entry=has_other,
                payload=command.data,
            )
        except PageNotEditableError as exc:
            _raise_as_http(exc)
        except (InvalidPagePayloadError, UnsupportedEntryStatusError) as exc:
            _raise_as_http(exc)

        entry = self.repository.execute_submit_plan(
            subject_id=command.subject_id,
            visit_id=command.visit_id,
            crf_template_id=command.crf_template_id,
            plan=plan,
            data=command.data,
            actor_user_id=command.actor_user_id,
        )
        page_state = self.repository.upsert_page_state(
            subject_id=command.subject_id,
            visit_id=command.visit_id,
            crf_template_id=command.crf_template_id,
            data=command.data,
            status="submitted",
            actor_user_id=command.actor_user_id,
        )
        return SubmitPageResult(entry_id=entry.pk, entry_status="submitted", page_status=page_state.status)
