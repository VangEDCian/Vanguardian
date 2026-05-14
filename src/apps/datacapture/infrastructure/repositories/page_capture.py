from django.core.exceptions import ValidationError
from django.db.models import Max

from apps.core.choices import (
    DataCaptureFieldReviewStatusChoices,
    DataCaptureFieldReviewTypeChoices,
    DataCapturePageEntryStatusChoices,
    DataCapturePageStateStatusChoices,
)
from apps.crf.models import CrfFieldTemplate
from apps.datacapture.infrastructure.models.capture import (
    DataCapturePageEntrySnapshot,
    DataCapturePageStateSnapshot,
    SubmitExecutionPlan,
)
from apps.datacapture.models import (
    DataCaptureFieldReview,
    DataCapturePageEntry,
    DataCapturePageState,
    DataCapturePageStateTransitionLog,
)


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
                "data_version",
                "current_entry_id",
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
            data_version=page_state.data_version,
            current_entry_id=page_state.current_entry_id,
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
            .exclude(status__in=[DataCapturePageEntryStatusChoices.CANCELLED, "canceled"])
            .only(
                "id",
                "page_state_id",
                "parent_entry_id",
                "entry_no",
                "entry_kind",
                "entry_version",
                "status",
                "data",
                "crf_template_id",
                "subject_id",
                "visit_id",
                "updated_by_id",
                "updated_at",
            )
            .order_by("-entry_no", "-id")
            .first()
        )
        if page_entry is None:
            return None
        return DataCapturePageEntrySnapshot(
            id=page_entry.pk,
            page_state_id=page_entry.page_state_id,
            parent_entry_id=page_entry.parent_entry_id,
            entry_no=page_entry.entry_no,
            entry_kind=page_entry.entry_kind,
            entry_version=page_entry.entry_version,
            status=page_entry.status,
            data=page_entry.data,
            crf_template_id=page_entry.crf_template_id,
            subject_id=page_entry.subject_id,
            visit_id=page_entry.visit_id,
            updated_by_id=page_entry.updated_by_id,
            updated_at=page_entry.updated_at,
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
                "page_state_id",
                "parent_entry_id",
                "entry_no",
                "entry_kind",
                "entry_version",
                "status",
                "data",
                "crf_template_id",
                "subject_id",
                "visit_id",
                "updated_by_id",
                "updated_at",
            )
            .order_by("-entry_no", "-id")
            .first()
        )
        if page_entry is None:
            return None
        return DataCapturePageEntrySnapshot(
            id=page_entry.pk,
            page_state_id=page_entry.page_state_id,
            parent_entry_id=page_entry.parent_entry_id,
            entry_no=page_entry.entry_no,
            entry_kind=page_entry.entry_kind,
            entry_version=page_entry.entry_version,
            status=page_entry.status,
            data=page_entry.data,
            crf_template_id=page_entry.crf_template_id,
            subject_id=page_entry.subject_id,
            visit_id=page_entry.visit_id,
            updated_by_id=page_entry.updated_by_id,
            updated_at=page_entry.updated_at,
        )

    @staticmethod
    def _entry_version_for_no(entry_no: int) -> str:
        return f"v{entry_no}"

    def create_initial_entry(
        self,
        *,
        page_state_id: int,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
        data: str,
        actor_user_id: int | None = None,
    ):
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
            page_state_id=page_state_id,
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
            created_by_id=actor_user_id,
            updated_by_id=actor_user_id,
        )

    def create_correction_draft_from_submitted_entry(
        self,
        *,
        page_state_id: int,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
        data: str,
        actor_user_id: int | None = None,
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
            page_state_id=page_state_id,
            parent_entry_id=latest.id,
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
            status=DataCapturePageEntryStatusChoices.CANCELLED,
            updated_at=self._now(),
            updated_by_id=actor_user_id,
        )
        return latest

    def upsert_page_state(
        self,
        *,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
        status: str,
        actor_user_id: int | None = None,
        trigger_source: str = "manual",
    ):
        """Create or update page state lifecycle fields only."""
        now = self._now()
        existing = (
            DataCapturePageState.objects.filter(
                subject_id=subject_id,
                visit_id=visit_id,
                crf_template_id=crf_template_id,
            )
            .order_by("id")
            .first()
        )
        if existing is not None:
            from_status = existing.status
            DataCapturePageState.objects.filter(pk=existing.pk).update(
                updated_at=now,
                deleted=False,
                status=status,
                updated_by_id=actor_user_id,
            )
            existing.refresh_from_db()
            self._record_page_state_transition(
                page_state=existing,
                from_status=from_status,
                to_status=status,
                actor_user_id=actor_user_id,
                trigger_source=trigger_source,
            )
            return existing
        page_state = DataCapturePageState.objects.create(
            created_at=now,
            updated_at=now,
            deleted=False,
            status=status,
            final_data="{}",
            data_version=1,
            crf_template_id=crf_template_id,
            subject_id=subject_id,
            visit_id=visit_id,
            created_by_id=actor_user_id,
            updated_by_id=actor_user_id,
        )
        self._record_page_state_transition(
            page_state=page_state,
            from_status=None,
            to_status=status,
            actor_user_id=actor_user_id,
            trigger_source=trigger_source,
        )
        return page_state

    def upsert_page_state_for_data_entry(
        self,
        *,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
        actor_user_id: int | None = None,
    ):
        page_state = DataCapturePageState.objects.filter(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
            deleted=False,
        ).first()
        if page_state is None:
            page_state = self.upsert_page_state(
                subject_id=subject_id,
                visit_id=visit_id,
                crf_template_id=crf_template_id,
                status=DataCapturePageStateStatusChoices.NOT_STARTED,
                actor_user_id=actor_user_id,
                trigger_source="system",
            )
        if page_state.status == DataCapturePageStateStatusChoices.NOT_STARTED:
            return self.upsert_page_state(
                subject_id=subject_id,
                visit_id=visit_id,
                crf_template_id=crf_template_id,
                status=DataCapturePageStateStatusChoices.IN_PROGRESS,
                actor_user_id=actor_user_id,
                trigger_source="manual",
            )
        return page_state

    def ensure_open_page_state_if_not_exists(
        self,
        *,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
        actor_user_id: int | None = None,
    ) -> bool:
        """Create a not-started ``PageState`` when none exists for the scope."""
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
            status=DataCapturePageStateStatusChoices.NOT_STARTED,
            actor_user_id=actor_user_id,
            trigger_source="system",
        )
        return True

    def ensure_draft_page_state_if_not_exists(self, **kwargs) -> bool:
        return self.ensure_open_page_state_if_not_exists(**kwargs)

    def execute_submit_plan(
        self,
        *,
        page_state_id: int,
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
                submitted_at=self._now(),
                submitted_by_id=actor_user_id,
                page_state_id=page_state_id,
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
                submitted_at=self._now(),
                submitted_by_id=actor_user_id,
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
                submitted_at=self._now(),
                submitted_by_id=actor_user_id,
                page_state_id=page_state_id,
                parent_entry_id=snap.id,
                subject_id=subject_id,
                visit_id=visit_id,
                crf_template_id=crf_template_id,
                created_by_id=actor_user_id,
                updated_by_id=actor_user_id,
            )

        raise RuntimeError(f"execute_submit_plan: unknown action {plan.action!r}")

    def submit_page_state_with_entry(
        self,
        *,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
        entry_id: int,
        final_data: str,
        actor_user_id: int | None = None,
        trigger_source: str = "manual",
    ):
        page_state = (
            DataCapturePageState.objects.filter(
                subject_id=subject_id,
                visit_id=visit_id,
                crf_template_id=crf_template_id,
                deleted=False,
            )
            .order_by("id")
            .first()
        )
        if page_state is None:
            page_state = self.upsert_page_state(
                subject_id=subject_id,
                visit_id=visit_id,
                crf_template_id=crf_template_id,
                status=DataCapturePageStateStatusChoices.NOT_STARTED,
                actor_user_id=actor_user_id,
                trigger_source="system",
            )
        now = self._now()
        from_status = page_state.status
        next_version = int(page_state.data_version or 1) + 1
        DataCapturePageState.objects.filter(pk=page_state.pk).update(
            updated_at=now,
            updated_by_id=actor_user_id,
            final_data=final_data,
            data_version=next_version,
            current_entry_id=entry_id,
            status=DataCapturePageStateStatusChoices.SUBMITTED,
            submitted_at=now,
            submitted_by_id=actor_user_id,
        )
        page_state.refresh_from_db()
        self._record_page_state_transition(
            page_state=page_state,
            from_status=from_status,
            to_status=DataCapturePageStateStatusChoices.SUBMITTED,
            actor_user_id=actor_user_id,
            trigger_source=trigger_source,
        )
        return page_state

    def mark_field_reviews_stale_for_changed_field_keys(
        self,
        *,
        page_state_id: int,
        crf_template_id: int,
        changed_field_keys: list[str],
        actor_user_id: int | None = None,
    ) -> int:
        if not changed_field_keys:
            return 0
        field_template_ids = list(
            CrfFieldTemplate.objects.filter(
                crf_template_id=crf_template_id,
                field_key__in=changed_field_keys,
                deleted=False,
            ).values_list("id", flat=True)
        )
        if not field_template_ids:
            return 0
        return DataCaptureFieldReview.objects.filter(
            page_state_id=page_state_id,
            field_template_id__in=field_template_ids,
            deleted=False,
        ).exclude(status__in=["stale", "waived"]).update(
            status="stale",
            updated_at=self._now(),
            updated_by_id=actor_user_id,
        )

    def start_page_review(
        self,
        *,
        page_state_id: int,
        actor_user_id: int | None = None,
    ):
        page_state = DataCapturePageState.objects.filter(pk=page_state_id, deleted=False).first()
        if page_state is None:
            raise ValidationError("No page state exists for this subject visit and form.")
        if page_state.status == DataCapturePageStateStatusChoices.UNDER_REVIEW:
            return page_state
        if page_state.status != DataCapturePageStateStatusChoices.SUBMITTED:
            raise ValidationError("Review can only start from a submitted page state.")
        now = self._now()
        from_status = page_state.status
        DataCapturePageState.objects.filter(pk=page_state.pk).update(
            updated_at=now,
            updated_by_id=actor_user_id,
            status=DataCapturePageStateStatusChoices.UNDER_REVIEW,
            review_started_at=now,
            review_started_by_id=actor_user_id,
        )
        page_state.refresh_from_db()
        self._record_page_state_transition(
            page_state=page_state,
            from_status=from_status,
            to_status=DataCapturePageStateStatusChoices.UNDER_REVIEW,
            actor_user_id=actor_user_id,
            trigger_source="review",
        )
        return page_state

    def ensure_field_reviews_for_page(
        self,
        *,
        page_state_id: int,
        field_template_ids: tuple[int, ...],
        data_version: int,
        actor_user_id: int | None = None,
        review_type: str = DataCaptureFieldReviewTypeChoices.DATA_REVIEW,
    ) -> int:
        if not field_template_ids:
            return 0
        now = self._now()
        existing_ids = set(
            DataCaptureFieldReview.objects.filter(
                page_state_id=page_state_id,
                field_template_id__in=field_template_ids,
                review_type=review_type,
                deleted=False,
            ).values_list("field_template_id", flat=True)
        )
        records = [
            DataCaptureFieldReview(
                created_at=now,
                updated_at=now,
                deleted=False,
                page_state_id=page_state_id,
                field_template_id=field_template_id,
                review_type=review_type,
                status=DataCaptureFieldReviewStatusChoices.NOT_REVIEWED,
                data_version=data_version,
                created_by_id=actor_user_id,
                updated_by_id=actor_user_id,
            )
            for field_template_id in field_template_ids
            if field_template_id not in existing_ids
        ]
        if not records:
            return 0
        DataCaptureFieldReview.objects.bulk_create(records, ignore_conflicts=True)
        return len(records)

    def verify_field_review(
        self,
        *,
        page_state_id: int,
        field_template_id: int,
        data_version: int,
        value_snapshot: str,
        actor_user_id: int | None = None,
        review_type: str = DataCaptureFieldReviewTypeChoices.DATA_REVIEW,
    ) -> None:
        now = self._now()
        review, _ = DataCaptureFieldReview.objects.get_or_create(
            page_state_id=page_state_id,
            field_template_id=field_template_id,
            review_type=review_type,
            defaults={
                "created_at": now,
                "updated_at": now,
                "deleted": False,
                "status": DataCaptureFieldReviewStatusChoices.NOT_REVIEWED,
                "data_version": data_version,
                "created_by_id": actor_user_id,
                "updated_by_id": actor_user_id,
            },
        )
        update_fields = {
            "updated_at": now,
            "updated_by_id": actor_user_id,
            "deleted": False,
            "status": DataCaptureFieldReviewStatusChoices.VERIFIED,
            "data_version": data_version,
            "value_snapshot": value_snapshot,
            "verified_at": now,
            "verified_by_id": actor_user_id,
        }
        if review.reviewed_at is None:
            update_fields["reviewed_at"] = now
            update_fields["reviewed_by_id"] = actor_user_id
        DataCaptureFieldReview.objects.filter(pk=review.pk).update(**update_fields)

    def map_valid_field_review_status_by_field_template_id(
        self,
        *,
        page_state_id: int,
        data_version: int,
        review_type: str = DataCaptureFieldReviewTypeChoices.DATA_REVIEW,
    ) -> dict[int, str]:
        rows = DataCaptureFieldReview.objects.filter(
            page_state_id=page_state_id,
            review_type=review_type,
            data_version=data_version,
            deleted=False,
        ).values("field_template_id", "status")
        return {int(row["field_template_id"]): str(row["status"] or "") for row in rows}

    def list_verified_or_waived_field_template_ids(
        self,
        *,
        page_state_id: int,
        data_version: int,
        review_type: str = DataCaptureFieldReviewTypeChoices.DATA_REVIEW,
    ) -> set[int]:
        return set(
            DataCaptureFieldReview.objects.filter(
                page_state_id=page_state_id,
                review_type=review_type,
                data_version=data_version,
                deleted=False,
                status__in=[
                    DataCaptureFieldReviewStatusChoices.VERIFIED,
                    DataCaptureFieldReviewStatusChoices.WAIVED,
                ],
            ).values_list("field_template_id", flat=True)
        )

    def find_page_verification_field_review_blockers(
        self,
        *,
        page_state_id: int,
        data_version: int,
        required_field_template_ids: tuple[int, ...],
        review_type: str = DataCaptureFieldReviewTypeChoices.DATA_REVIEW,
    ) -> list[str]:
        if not required_field_template_ids:
            return []
        valid_statuses = {
            DataCaptureFieldReviewStatusChoices.VERIFIED,
            DataCaptureFieldReviewStatusChoices.WAIVED,
        }
        status_by_field = self.map_valid_field_review_status_by_field_template_id(
            page_state_id=page_state_id,
            data_version=data_version,
            review_type=review_type,
        )
        blockers: list[str] = []
        for field_template_id in required_field_template_ids:
            status = status_by_field.get(int(field_template_id))
            if status not in valid_statuses:
                blockers.append(f"field_review_not_ready:{field_template_id}")
        return blockers

    def verify_page_state_if_ready(
        self,
        *,
        page_state_id: int,
        actor_user_id: int | None = None,
    ) -> str:
        page_state = DataCapturePageState.objects.filter(pk=page_state_id, deleted=False).first()
        if page_state is None:
            raise ValidationError("No page state exists for this subject visit and form.")
        if page_state.status not in [
            DataCapturePageStateStatusChoices.SUBMITTED,
            DataCapturePageStateStatusChoices.UNDER_REVIEW,
        ]:
            raise ValidationError("Page can only be verified from submitted or under_review state.")
        now = self._now()
        from_status = page_state.status
        DataCapturePageState.objects.filter(pk=page_state.pk).update(
            updated_at=now,
            updated_by_id=actor_user_id,
            status=DataCapturePageStateStatusChoices.VERIFIED,
            verified_at=now,
            verified_by_id=actor_user_id,
            verified_data_version=page_state.data_version,
        )
        page_state.refresh_from_db()
        self._record_page_state_transition(
            page_state=page_state,
            from_status=from_status,
            to_status=DataCapturePageStateStatusChoices.VERIFIED,
            actor_user_id=actor_user_id,
            trigger_source="review",
        )
        return DataCapturePageStateStatusChoices.VERIFIED.value

    def map_latest_submitted_entry_updated_by_id_by_subject_ids(
        self, *, subject_ids: tuple[int, ...]
    ) -> dict[int, int | None]:
        if not subject_ids:
            return {}
        result: dict[int, int | None] = {}
        entries = (
            DataCapturePageEntry.objects.filter(
                subject_id__in=subject_ids,
                deleted=False,
                status=DataCapturePageEntryStatusChoices.SUBMITTED,
            )
            .only("subject_id", "updated_by_id", "updated_at", "id")
            .order_by("subject_id", "-updated_at", "-id")
        )
        for entry in entries:
            if entry.subject_id not in result:
                result[entry.subject_id] = entry.updated_by_id
        return result

    def update_page_state_final_data_and_status(
        self,
        *,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
        final_data: str | None,
        status: str,
        actor_user_id: int | None = None,
    ) -> None:
        """Persist ``final_data`` (JSON string or database NULL) and ``status`` for the scoped page state."""
        now = self._now()
        page_state = DataCapturePageState.objects.filter(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
            deleted=False,
        ).first()
        if page_state is None:
            raise ValidationError(
                "Could not persist verification: page state update affected 0 rows.",
            )
        from_status = page_state.status
        rows_updated = DataCapturePageState.objects.filter(pk=page_state.pk).update(
            final_data=final_data,
            status=status,
            updated_at=now,
            updated_by_id=actor_user_id,
        )
        if rows_updated == 0:
            raise ValidationError(
                "Could not persist verification: page state update affected 0 rows.",
            )
        page_state.refresh_from_db()
        self._record_page_state_transition(
            page_state=page_state,
            from_status=from_status,
            to_status=status,
            actor_user_id=actor_user_id,
            trigger_source="review",
        )

    def _record_page_state_transition(
        self,
        *,
        page_state,
        from_status: str | None,
        to_status: str,
        actor_user_id: int | None,
        trigger_source: str,
    ) -> None:
        if from_status == to_status:
            return
        DataCapturePageStateTransitionLog.objects.create(
            created_at=self._now(),
            page_state_id=page_state.pk,
            from_status=from_status,
            to_status=to_status,
            data_version=getattr(page_state, "data_version", None),
            trigger_source=trigger_source,
            actor_id=actor_user_id,
        )

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
