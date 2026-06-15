from django.core.management.base import BaseCommand
from django.db import transaction

from apps.identity.application.permissions import (
    ALL_PERMISSION_DEFINITIONS,
)
from apps.identity.models import IdentityPermission


class Command(BaseCommand):
    help = "Seed identity_permission records from the central permission registry."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be seeded without writing to the database.",
        )

    def handle(self, *args, **options):
        summary = seed_permissions(dry_run=options["dry_run"])
        self.stdout.write(self.style.SUCCESS(summary.message))


class SeedPermissionSummary:
    def __init__(self):
        self.created = 0
        self.updated = 0
        self.unchanged = 0
        self.ambiguous = 0

    def add(self, result):
        current_value = getattr(self, result)
        setattr(self, result, current_value + 1)

    @property
    def message(self):
        return (
            "Seed permission complete: "
            f"{self.created} created, "
            f"{self.updated} updated, "
            f"{self.unchanged} unchanged, "
            f"{self.ambiguous} ambiguous."
        )


def seed_permissions(*, dry_run):
    summary = SeedPermissionSummary()
    with transaction.atomic():
        for definition in ALL_PERMISSION_DEFINITIONS:
            result = _sync_permission(definition, dry_run=dry_run)
            summary.add(result)

        if dry_run:
            transaction.set_rollback(True)

    return summary


def _sync_permission(definition, *, dry_run):
    label = definition.label or definition.codename
    matching_permissions = list(
        IdentityPermission.objects.filter(
            app_label=definition.app_label,
            codename=definition.codename,
        )
    )

    if len(matching_permissions) > 1:
        for permission in matching_permissions:
            if permission.name != label and not dry_run:
                permission.name = label
                permission.save(update_fields=["name"])
        return "ambiguous"

    if matching_permissions:
        permission = matching_permissions[0]
        if permission.name == label:
            return "unchanged"
        if not dry_run:
            permission.name = label
            permission.save(update_fields=["name"])
        return "updated"

    if not dry_run:
        IdentityPermission.objects.create(
            app_label=definition.app_label,
            codename=definition.codename,
            name=label,
        )
    return "created"


__all__ = ["SeedPermissionSummary", "seed_permissions"]
