import json
from dataclasses import dataclass
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.core.form_data_document import (
    FORM_DATA_FORMAT,
    FormDataNormalizationError,
    is_canonical_form_data,
)
from apps.datacapture.infrastructure.repositories import DjangoDataCapturePageRepository
from apps.datacapture.models import DataCapturePageEntry, DataCapturePageState


@dataclass
class MigrationStats:
    scanned: int = 0
    already_canonical: int = 0
    migratable: int = 0
    invalid_json: int = 0
    missing_template: int = 0
    unmapped_fields: int = 0
    updated: int = 0
    unmapped_examples: list[str] | None = None


class Command(BaseCommand):
    help = "Migrate PageEntry.data and PageState.final_data from legacy flat JSON to edc.form_data.v1."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report only; this is the default.")
        parser.add_argument("--apply", action="store_true", help="Apply updates.")
        parser.add_argument("--study-id", type=int, default=None)
        parser.add_argument("--form-code", default=None)
        parser.add_argument("--batch-size", type=int, default=500)
        parser.add_argument("--allow-unmapped", action="store_true")

    def handle(self, *args, **options):
        apply = bool(options["apply"])
        if options["dry_run"] and apply:
            raise CommandError("Use either --dry-run or --apply, not both.")
        batch_size = max(int(options["batch_size"] or 500), 1)
        repository = DjangoDataCapturePageRepository()
        entry_stats = self._process_model(
            model=DataCapturePageEntry,
            data_field="data",
            repository=repository,
            apply=apply,
            batch_size=batch_size,
            study_id=options["study_id"],
            form_code=options["form_code"],
            allow_unmapped=bool(options["allow_unmapped"]),
        )
        state_stats = self._process_model(
            model=DataCapturePageState,
            data_field="final_data",
            repository=repository,
            apply=apply,
            batch_size=batch_size,
            study_id=options["study_id"],
            form_code=options["form_code"],
            allow_unmapped=bool(options["allow_unmapped"]),
        )
        self._write_stats("PageEntry.data", entry_stats)
        self._write_stats("PageState.final_data", state_stats)
        self.stdout.write(
            "Audit integration: not applied here; hook FORM_DATA_JSON_V1_MIGRATION into the audit adapter when available."
        )

    def _base_queryset(self, *, model, study_id: int | None, form_code: str | None):
        qs = model.objects.filter(deleted=False).select_related("crf_template").order_by("id")
        if study_id is not None:
            qs = qs.filter(crf_template__study_id=study_id)
        if form_code:
            qs = qs.filter(crf_template__code=form_code)
        return qs.only("id", "crf_template_id", "crf_template__code", "crf_template__version")

    def _process_model(
        self,
        *,
        model,
        data_field: str,
        repository: DjangoDataCapturePageRepository,
        apply: bool,
        batch_size: int,
        study_id: int | None,
        form_code: str | None,
        allow_unmapped: bool,
    ) -> MigrationStats:
        stats = MigrationStats()
        examples: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
        pending: list[tuple[Any, str]] = []
        for row in self._base_queryset(model=model, study_id=study_id, form_code=form_code).iterator(chunk_size=batch_size):
            stats.scanned += 1
            raw_value = getattr(row, data_field)
            parsed, invalid = self._parse_json(raw_value)
            if invalid:
                stats.invalid_json += 1
                continue
            if is_canonical_form_data(parsed):
                stats.already_canonical += 1
                continue
            if repository.get_form_template_snapshot(crf_template_id=row.crf_template_id) is None:
                stats.missing_template += 1
                continue
            try:
                converted = repository.normalize_form_data_json_for_storage(
                    crf_template_id=row.crf_template_id,
                    data=raw_value or "{}",
                    entry_version=getattr(row, "entry_version", None),
                    strict=not allow_unmapped,
                )
            except FormDataNormalizationError as exc:
                stats.unmapped_fields += 1
                if stats.unmapped_examples is None:
                    stats.unmapped_examples = []
                if len(stats.unmapped_examples) < 5:
                    fields = ", ".join(exc.unmapped_fields[:10]) or "(unknown)"
                    stats.unmapped_examples.append(f"{model.__name__}#{row.pk}: {fields}")
                continue
            converted_doc = json.loads(converted)
            if converted_doc.get("format") != FORM_DATA_FORMAT:
                stats.invalid_json += 1
                continue
            stats.migratable += 1
            if len(examples) < 3:
                examples.append((row.pk, parsed, converted_doc))
            if apply:
                pending.append((row, converted))
                if len(pending) >= batch_size:
                    stats.updated += self._flush_updates(data_field=data_field, pending=pending)
                    pending = []
        if apply and pending:
            stats.updated += self._flush_updates(data_field=data_field, pending=pending)
        for object_id, before, after in examples:
            self.stdout.write(f"Example {model.__name__}#{object_id} before={before}")
            self.stdout.write(f"Example {model.__name__}#{object_id} after={after}")
        return stats

    @staticmethod
    def _parse_json(raw_value) -> tuple[dict, bool]:
        try:
            parsed = json.loads(raw_value or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}, True
        if not isinstance(parsed, dict):
            return {}, True
        return parsed, False

    @staticmethod
    def _flush_updates(*, data_field: str, pending: list[tuple[Any, str]]) -> int:
        with transaction.atomic():
            for row, converted in pending:
                setattr(row, data_field, converted)
                row.updated_at = timezone.now()
                row.save(update_fields=[data_field, "updated_at"])
        return len(pending)

    def _write_stats(self, label: str, stats: MigrationStats) -> None:
        self.stdout.write(f"{label}: scanned={stats.scanned}")
        self.stdout.write(f"{label}: already_canonical={stats.already_canonical}")
        self.stdout.write(f"{label}: legacy_migratable={stats.migratable}")
        self.stdout.write(f"{label}: invalid_json={stats.invalid_json}")
        self.stdout.write(f"{label}: missing_template={stats.missing_template}")
        self.stdout.write(f"{label}: unmapped_fields={stats.unmapped_fields}")
        for example in stats.unmapped_examples or []:
            self.stdout.write(f"{label}: unmapped_example={example}")
        self.stdout.write(f"{label}: updated={stats.updated}")
