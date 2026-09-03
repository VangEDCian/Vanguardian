from django.core.management.base import BaseCommand

from apps.identity.application.services.permission_catalog_sync import (
    PermissionCatalogSyncService,
)


class Command(BaseCommand):
    help = (
        "Synchronize identity_permission from the central permission catalog. "
        "This command does not create roles or role-permission mappings."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report catalog changes without writing to the database.",
        )

    def handle(self, *args, **options):
        result = PermissionCatalogSyncService().execute(
            dry_run=options["dry_run"],
        )
        mode = "dry run" if result.dry_run else "sync"
        self.stdout.write(
            self.style.SUCCESS(
                f"Permission catalog {mode} complete: "
                f"{result.created} created, "
                f"{result.updated} updated, "
                f"{result.unchanged} unchanged, "
                f"{result.total} total."
            )
        )


__all__ = ["Command"]
