from dataclasses import dataclass


@dataclass(frozen=True)
class DataCapturePageStateSnapshot:
    id: int
    status: str
    final_data: str | None
    crf_template_id: int
    subject_id: int
    visit_id: int
    study_id: int
    study_version: str
    event_definition_id: int


@dataclass(frozen=True)
class DataCaptureFactMappingRule:
    id: int
    source_path: str
    fact_key: str
    operator: str
    expected_value: str | None
    value_type: str
    default_value: str | None = None
    field_code: str | None = None


__all__ = [
    "DataCaptureFactMappingRule",
    "DataCapturePageStateSnapshot",
]
