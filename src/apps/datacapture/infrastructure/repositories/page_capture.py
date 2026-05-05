from apps.datacapture.infrastructure.models.capture import (
    DataCapturePageEntrySnapshot,
    DataCapturePageStateSnapshot,
    SubmitExecutionPlan,
)
from django.db.models import Max
from apps.core.choices import (
    DataCapturePageEntryStatusChoices,
    DataCapturePageStateStatusChoices,
)
from apps.datacapture.models import DataCapturePageEntry, DataCapturePageState


class DjangoDataCapturePageRepository:
    def get_page_state(self, *, subject_id: int, visit_id: int, crf_template_id: int):
        page_state = (
            DataCapturePageState.objects.filter(
                subject_id=subject_id,
                visit_id=visit_id,
                crf_template_id=crf_template_id,
                deleted=False,
            )
            .only(
                "id",
                "status",
                "final_data",
                "crf_template_id",
                "subject_id",
                "visit_id",
                "visit__study_id",
                "visit__study_version",
                "visit__event_definition_id",
            )
            .select_related("visit")
            .first()
        )
        if page_state is None:
            return None
        visit = page_state.visit
        return DataCapturePageStateSnapshot(
            id=page_state.pk,
            status=page_state.status,
            final_data=page_state.final_data,
            crf_template_id=page_state.crf_template_id,
            subject_id=page_state.subject_id,
            visit_id=page_state.visit_id,
            study_id=visit.study_id,
            study_version=visit.study_version,
            event_definition_id=visit.event_definition_id,
        )

    def get_latest_entry(self, *, subject_id: int, visit_id: int, crf_template_id: int):
        page_entry = (
            DataCapturePageEntry.objects.filter(
                subject_id=subject_id,
                visit_id=visit_id,
                crf_template_id=crf_template_id,
                deleted=False,
            )
            .exclude(status=DataCapturePageEntryStatusChoices.CANCELED)
            .only(
                "id",
                "entry_no",
                "entry_kind",
                "entry_version",
                "status",
                "data",
                "crf_template_id",
                "subject_id",
                "visit_id",
            )
            .order_by("-entry_no", "-id")
            .first()
        )
        if page_entry is None:
            return None
        return DataCapturePageEntrySnapshot(
            id=page_entry.pk,
            entry_no=page_entry.entry_no,
            entry_kind=page_entry.entry_kind,
            entry_version=page_entry.entry_version,
            status=page_entry.status,
            data=page_entry.data,
            crf_template_id=page_entry.crf_template_id,
            subject_id=page_entry.subject_id,
            visit_id=page_entry.visit_id,
        )

    def get_latest_submitted_entry(self, *, subject_id: int, visit_id: int, crf_template_id: int):
        page_entry = (
            DataCapturePageEntry.objects.filter(
                subject_id=subject_id,
                visit_id=visit_id,
                crf_template_id=crf_template_id,
                deleted=False,
                status=DataCapturePageEntryStatusChoices.SUBMITTED,
            )
            .only(
                "id",
                "entry_no",
                "entry_kind",
                "entry_version",
                "status",
                "data",
                "crf_template_id",
                "subject_id",
                "visit_id",
            )
            .order_by("-entry_no", "-id")
            .first()
        )
        if page_entry is None:
            return None
        return DataCapturePageEntrySnapshot(
            id=page_entry.pk,
            entry_no=page_entry.entry_no,
            entry_kind=page_entry.entry_kind,
            entry_version=page_entry.entry_version,
            status=page_entry.status,
            data=page_entry.data,
            crf_template_id=page_entry.crf_template_id,
            subject_id=page_entry.subject_id,
            visit_id=page_entry.visit_id,
        )

    @staticmethod
    def _entry_version_for_no(entry_no: int) -> str:
        return f"v{entry_no}"

    def create_initial_entry(self, *, subject_id: int, visit_id: int, crf_template_id: int, data: str, actor_user_id: int | None = None):
        next_entry_no = self._next_entry_no(subject_id=subject_id, visit_id=visit_id, crf_template_id=crf_template_id)
        return DataCapturePageEntry.objects.create(
            created_at=self._now(),
            updated_at=self._now(),
            deleted=False,
            entry_no=next_entry_no,
            entry_kind="initial",
            entry_version=self._entry_version_for_no(next_entry_no),
            data=data,
            status=DataCapturePageEntryStatusChoices.DRAFT,
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
            created_by_id=actor_user_id,
            updated_by_id=actor_user_id,
        )

    def create_correction_draft_from_submitted_entry(
        self, *, subject_id: int, visit_id: int, crf_template_id: int, data: str, actor_user_id: int | None = None
    ):
        """Save-draft after a submitted row: new correction draft; prior submitted row unchanged (6.2)."""
        latest = self.get_latest_entry(subject_id=subject_id, visit_id=visit_id, crf_template_id=crf_template_id)
        assert latest is not None and latest.status == DataCapturePageEntryStatusChoices.SUBMITTED
        next_entry_no = self._next_entry_no(subject_id=subject_id, visit_id=visit_id, crf_template_id=crf_template_id)
        entry_version = self._entry_version_for_no(next_entry_no)
        return DataCapturePageEntry.objects.create(
            created_at=self._now(),
            updated_at=self._now(),
            deleted=False,
            entry_no=next_entry_no,
            entry_kind="correction",
            entry_version=entry_version,
            data=data,
            status=DataCapturePageEntryStatusChoices.DRAFT,
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
            created_by_id=actor_user_id,
            updated_by_id=actor_user_id,
        )

    def supersede_submitted_entries_except(
        self,
        *,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
        keep_entry_id: int,
        actor_user_id: int | None = None,
    ) -> int:
        """Mark all submitted rows except ``keep_entry_id`` as superseded (submit flow 6.3)."""
        return DataCapturePageEntry.objects.filter(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
            deleted=False,
            status=DataCapturePageEntryStatusChoices.SUBMITTED,
        ).exclude(pk=keep_entry_id).update(
            status=DataCapturePageEntryStatusChoices.SUPERSEDED,
            updated_at=self._now(),
            updated_by_id=actor_user_id,
        )

    def has_other_submitted_entry(
        self, *, subject_id: int, visit_id: int, crf_template_id: int, exclude_entry_id: int
    ) -> bool:
        return DataCapturePageEntry.objects.filter(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
            deleted=False,
            status=DataCapturePageEntryStatusChoices.SUBMITTED,
        ).exclude(pk=exclude_entry_id).exists()

    def get_page_state_by_scope(self, *, subject_id: int, visit_id: int, crf_template_id: int):
        return self.get_page_state(subject_id=subject_id, visit_id=visit_id, crf_template_id=crf_template_id)

    def get_current_entry(self, *, subject_id: int, visit_id: int, crf_template_id: int):
        return self.get_latest_entry(subject_id=subject_id, visit_id=visit_id, crf_template_id=crf_template_id)

    def update_latest_draft_entry_data(
        self, *, subject_id: int, visit_id: int, crf_template_id: int, data: str, actor_user_id: int | None = None
    ):
        latest = self.get_latest_entry(subject_id=subject_id, visit_id=visit_id, crf_template_id=crf_template_id)
        if latest is None or latest.status != DataCapturePageEntryStatusChoices.DRAFT:
            return latest
        DataCapturePageEntry.objects.filter(pk=latest.id).update(
            data=data,
            updated_at=self._now(),
            updated_by_id=actor_user_id,
        )
        return self.get_latest_entry(subject_id=subject_id, visit_id=visit_id, crf_template_id=crf_template_id)

    def cancel_latest_draft_entry(
        self, *, subject_id: int, visit_id: int, crf_template_id: int, actor_user_id: int | None = None
    ):
        latest = self.get_latest_entry(subject_id=subject_id, visit_id=visit_id, crf_template_id=crf_template_id)
        if latest is None or latest.status != DataCapturePageEntryStatusChoices.DRAFT:
            return None
        DataCapturePageEntry.objects.filter(pk=latest.id).update(
            status=DataCapturePageEntryStatusChoices.CANCELED,
            updated_at=self._now(),
            updated_by_id=actor_user_id,
        )
        return latest

    def upsert_page_state(self, *, subject_id: int, visit_id: int, crf_template_id: int, data: str, status: str, actor_user_id: int | None = None):
        page_state, _ = DataCapturePageState.objects.update_or_create(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
            defaults={
                "created_at": self._now(),
                "updated_at": self._now(),
                "deleted": False,
                "status": status,
                "final_data": data,
                "updated_by_id": actor_user_id,
            },
        )
        return page_state

    def ensure_draft_page_state_if_not_exists(
        self,
        *,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
        final_data: str = "{}",
        actor_user_id: int | None = None,
    ) -> bool:
        """Create a draft ``PageState`` when none exists for the scope. Returns True if created."""
        exists = DataCapturePageState.objects.filter(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
            deleted=False,
        ).exists()
        if exists:
            return False
        self.upsert_page_state(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
            data=final_data,
            status=DataCapturePageStateStatusChoices.DRAFT,
            actor_user_id=actor_user_id,
        )
        return True

    def execute_submit_plan(
        self,
        *,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
        plan: SubmitExecutionPlan,
        data: str,
        actor_user_id: int | None = None,
    ):
        """Persist submit outcome described by a domain ``SubmitExecutionPlan`` (no branching here)."""
        if plan.action == "initial_submitted":
            next_entry_no = self._next_entry_no(subject_id=subject_id, visit_id=visit_id, crf_template_id=crf_template_id)
            return DataCapturePageEntry.objects.create(
                created_at=self._now(),
                updated_at=self._now(),
                deleted=False,
                entry_no=next_entry_no,
                entry_kind="initial",
                entry_version=self._entry_version_for_no(next_entry_no),
                data=data,
                status=DataCapturePageEntryStatusChoices.SUBMITTED,
                subject_id=subject_id,
                visit_id=visit_id,
                crf_template_id=crf_template_id,
                created_by_id=actor_user_id,
                updated_by_id=actor_user_id,
            )

        if plan.action == "promote_draft":
            assert plan.draft_entry_id is not None
            if plan.supersede_other_submitted_before_promote:
                self.supersede_submitted_entries_except(
                    subject_id=subject_id,
                    visit_id=visit_id,
                    crf_template_id=crf_template_id,
                    keep_entry_id=plan.draft_entry_id,
                    actor_user_id=actor_user_id,
                )
            DataCapturePageEntry.objects.filter(pk=plan.draft_entry_id).update(
                updated_at=self._now(),
                updated_by_id=actor_user_id,
                data=data,
                status=DataCapturePageEntryStatusChoices.SUBMITTED,
            )
            return DataCapturePageEntry.objects.get(pk=plan.draft_entry_id)

        if plan.action == "replace_submitted":
            snap = plan.superseded_entry_snapshot
            assert snap is not None
            DataCapturePageEntry.objects.filter(pk=snap.id).update(
                updated_at=self._now(),
                updated_by_id=actor_user_id,
                status=DataCapturePageEntryStatusChoices.SUPERSEDED,
            )
            next_entry_no = self._next_entry_no(subject_id=subject_id, visit_id=visit_id, crf_template_id=crf_template_id)
            entry_version = self._entry_version_for_no(next_entry_no)
            return DataCapturePageEntry.objects.create(
                created_at=self._now(),
                updated_at=self._now(),
                deleted=False,
                entry_no=next_entry_no,
                entry_kind="correction",
                entry_version=entry_version,
                data=data,
                status=DataCapturePageEntryStatusChoices.SUBMITTED,
                subject_id=subject_id,
                visit_id=visit_id,
                crf_template_id=crf_template_id,
                created_by_id=actor_user_id,
                updated_by_id=actor_user_id,
            )

        raise RuntimeError(f"execute_submit_plan: unknown action {plan.action!r}")

    def _next_entry_no(self, *, subject_id: int, visit_id: int, crf_template_id: int) -> int:
        max_entry_no = (
            DataCapturePageEntry.objects.filter(
                subject_id=subject_id,
                visit_id=visit_id,
                crf_template_id=crf_template_id,
                deleted=False,
            ).aggregate(max_entry_no=Max("entry_no")).get("max_entry_no")
        )
        return 1 if max_entry_no is None else int(max_entry_no) + 1

    @staticmethod
    def _now():
        from django.utils import timezone

        return timezone.now()
