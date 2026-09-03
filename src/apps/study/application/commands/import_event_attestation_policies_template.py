from dataclasses import dataclass

from apps.study.application.exceptions import (
    EventAttestationPolicyImportDependencyError as EventAttestationPolicyImportDependencyError,
)
from apps.study.application.exceptions import (
    EventAttestationPolicyImportFormatError as EventAttestationPolicyImportFormatError,
)
from apps.study.application.exceptions import (
    EventAttestationPolicyImportTemplateError as EventAttestationPolicyImportTemplateError,
)


@dataclass(frozen=True)
class ImportStudyEventAttestationPoliciesTemplateCommand:
    actor_user_id: int
    selected_study_id: int
    study_id: int
    file_name: str
    file_content: bytes


@dataclass(frozen=True)
class EventAttestationPolicyImportIssue:
    sheet_name: str
    row_number: int
    identifier: str
    reason: str


@dataclass(frozen=True)
class ImportStudyEventAttestationPoliciesTemplateResult:
    total_rows: int
    created_count: int
    updated_count: int
    skipped_count: int
    issues: tuple[EventAttestationPolicyImportIssue, ...] = ()
    warnings: tuple[str, ...] = ()


__all__ = [
    "EventAttestationPolicyImportDependencyError",
    "EventAttestationPolicyImportFormatError",
    "EventAttestationPolicyImportIssue",
    "EventAttestationPolicyImportTemplateError",
    "ImportStudyEventAttestationPoliciesTemplateCommand",
    "ImportStudyEventAttestationPoliciesTemplateResult",
]
