from dataclasses import dataclass

from apps.identity.application.permissions import ALL_PERMISSION_DEFINITIONS
from apps.identity.infrastructure.permission_catalog import (
    DjangoPermissionCatalogRepository,
)


@dataclass(frozen=True)
class PermissionCatalogSyncResult:
    created: int
    updated: int
    unchanged: int
    dry_run: bool

    @property
    def total(self) -> int:
        return self.created + self.updated + self.unchanged


class PermissionCatalogSyncService:
    repository_class = DjangoPermissionCatalogRepository

    def __init__(self, *, repository=None):
        self.repository = repository or self.repository_class()

    def execute(self, *, dry_run: bool = False) -> PermissionCatalogSyncResult:
        counts = self.repository.sync_definitions(
            definitions=ALL_PERMISSION_DEFINITIONS,
            dry_run=dry_run,
        )
        return PermissionCatalogSyncResult(
            created=counts["created"],
            updated=counts["updated"],
            unchanged=counts["unchanged"],
            dry_run=dry_run,
        )


__all__ = [
    "PermissionCatalogSyncResult",
    "PermissionCatalogSyncService",
]
