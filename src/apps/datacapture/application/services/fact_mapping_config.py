from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.datacapture.infrastructure.repositories import DjangoDataCaptureFactMappingRepository
from apps.study.application.exceptions import FactMappingImportConflictError


@dataclass(frozen=True)
class DataCaptureFactMappingUpsertResult:
    outcome: str
    fact_mapping_id: int


class DataCaptureFactMappingConfigService:
    repository_class = DjangoDataCaptureFactMappingRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def upsert_fact_mapping(
        self,
        *,
        study_id: int,
        study_version: str,
        event_definition_id: int,
        crf_template_id: int,
        field_code: str | None,
        source_path: str,
        fact_key: str,
        operator: str,
        expected_value: str | None,
        value_type: str,
        default_value: str | None,
        display_order: int,
        actor_user_id: int,
        now=None,
    ) -> DataCaptureFactMappingUpsertResult:
        now = now or timezone.now()
        defaults = {
            "field_code": field_code,
            "source_path": source_path,
            "operator": operator,
            "expected_value": expected_value,
            "value_type": value_type,
            "default_value": default_value,
            "is_enabled": True,
            "display_order": display_order,
            "deleted": False,
            "updated_at": now,
            "updated_by_id": actor_user_id,
        }

        try:
            with transaction.atomic():
                fact_mapping = self.repository.get_fact_mapping_for_import(
                    study_id=study_id,
                    study_version=study_version,
                    event_definition_id=event_definition_id,
                    crf_template_id=crf_template_id,
                    fact_key=fact_key,
                )
                if fact_mapping is not None and int(getattr(fact_mapping, "crf_template_id", 0) or 0) != int(crf_template_id):
                    raise FactMappingImportConflictError(
                        "Fact Key already exists in this study/event/version scope and is bound to another form."
                    )
                if fact_mapping is None:
                    fact_mapping = self.repository.create_fact_mapping(
                        study_id=study_id,
                        study_version=study_version,
                        event_definition_id=event_definition_id,
                        crf_template_id=crf_template_id,
                        fact_key=fact_key,
                        created_at=now,
                        created_by_id=actor_user_id,
                        **defaults,
                    )
                    return DataCaptureFactMappingUpsertResult(
                        outcome="created",
                        fact_mapping_id=fact_mapping.pk,
                    )

                for field_name, value in defaults.items():
                    setattr(fact_mapping, field_name, value)
                self.repository.save_fact_mapping(fact_mapping, update_fields=list(defaults.keys()))
                return DataCaptureFactMappingUpsertResult(
                    outcome="updated",
                    fact_mapping_id=fact_mapping.pk,
                )
        except IntegrityError as exc:
            raise FactMappingImportConflictError(
                "Fact Key already exists in this study/event/version scope and is bound to another form."
            ) from exc


__all__ = [
    "DataCaptureFactMappingConfigService",
    "DataCaptureFactMappingUpsertResult",
]
