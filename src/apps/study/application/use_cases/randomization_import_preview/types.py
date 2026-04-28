from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RandomizationImportColumn:
    key: str
    label: str
    data_type: str = "string"
    required: bool = True
    max_length: int | None = None
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class RandomizationImportIssue:
    row_number: int
    identifier: str
    column_label: str
    reason: str


@dataclass(frozen=True)
class RandomizationImportParsedRow:
    row_number: int
    identifier: str
    values: dict[str, Any]


@dataclass(frozen=True)
class RandomizationImportPreviewRow:
    row_number: int
    values: tuple[Any, ...]


@dataclass(frozen=True)
class RandomizationImportPreviewResult:
    columns: tuple[RandomizationImportColumn, ...]
    preview_rows: tuple[RandomizationImportPreviewRow, ...]
    parsed_rows: tuple[RandomizationImportParsedRow, ...]
    total_rows: int
    issues: tuple[RandomizationImportIssue, ...] = ()


class RandomizationImportDependencyError(Exception):
    """Raised when a workbook parser dependency is unavailable."""


class RandomizationImportFormatError(Exception):
    """Raised when the uploaded import file structure is invalid."""
