from dataclasses import dataclass


@dataclass(frozen=True)
class CommitNng31MasterListCommand:
    actor_user_id: int
    study_id: int
    file_name: str
    file_content: bytes
    master_list_version: str


@dataclass(frozen=True)
class CommitNng31MasterListResult:
    total_rows: int
    created_count: int
    updated_count: int
    scheme_id: int
    checksum: str
    master_list_version: str
    assigned_bypass_count: int = 0


@dataclass(frozen=True)
class ApproveNng31MasterListCommand:
    actor_user_id: int
    study_id: int
    scheme_id: int
    expected_checksum: str


@dataclass(frozen=True)
class ApproveNng31MasterListResult:
    scheme_id: int
    checksum: str


__all__ = [
    "ApproveNng31MasterListCommand",
    "ApproveNng31MasterListResult",
    "CommitNng31MasterListCommand",
    "CommitNng31MasterListResult",
]
