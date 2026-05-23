from dataclasses import dataclass


@dataclass(frozen=True)
class FinalizeEligibilityAssessmentCommand:
    study_id: int
    site_id: int
    subject_id: int
    assessment_type: str
    source_context: str
    source_object_type: str
    source_object_id: int | None
    study_version: str
    actor_id: int | None
    event_instance_id: int | None = None
    source_page_state_id: int | None = None
    source_page_entry_id: int | None = None
    source_data_version: int | None = None
    source_data_hash: str | None = None
    protocol_version: str | None = None
    crf_version: str | None = None
    rule_code: str | None = None
    rule_version: str | None = None
    conclusion_field_key: str | None = None
    force_result: str | None = None
    reason_code: str | None = None
    reason_text: str | None = None


@dataclass(frozen=True)
class RetractEligibilityAssessmentCommand:
    study_id: int
    subject_id: int
    assessment_id: int
    actor_id: int | None
    reason_code: str
    reason_text: str


@dataclass(frozen=True)
class MarkEligibilityStaleOnSourceDataChangeCommand:
    source_context: str
    source_object_type: str | None = None
    source_object_id: int | None = None
    source_page_state_id: int | None = None
    source_page_entry_id: int | None = None
    source_data_hash: str | None = None
    actor_id: int | None = None
    reason_code: str | None = "source_data_changed"
    reason_text: str | None = "Eligibility source data changed."


@dataclass(frozen=True)
class EnrollSubjectCommand:
    study_id: int
    site_id: int
    subject_id: int
    actor_id: int | None
    assessment_type: str = "SCREENING"
    reason_code: str | None = None
    reason_text: str | None = None


@dataclass(frozen=True)
class EligibilityAssessmentResult:
    assessment_id: int
    result: str
    assessment_status: str
    is_current: bool
    gate_result: str | None = None


__all__ = [
    "EligibilityAssessmentResult",
    "EnrollSubjectCommand",
    "FinalizeEligibilityAssessmentCommand",
    "MarkEligibilityStaleOnSourceDataChangeCommand",
    "RetractEligibilityAssessmentCommand",
]
