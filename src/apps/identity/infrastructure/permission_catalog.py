from django.db import transaction

from apps.identity.models import IdentityPermission


class DjangoPermissionCatalogRepository:
    @transaction.atomic
    def sync_definitions(self, *, definitions, dry_run: bool) -> dict[str, int]:
        counts = {
            "created": 0,
            "updated": 0,
            "unchanged": 0,
        }
        for definition in definitions:
            permission, created = IdentityPermission.objects.get_or_create(
                app_label=definition.app_label,
                codename=definition.codename,
                defaults={"name": definition.label},
            )
            if created:
                counts["created"] += 1
                continue
            if permission.name == definition.label:
                counts["unchanged"] += 1
                continue
            permission.name = definition.label
            permission.save(update_fields=["name"])
            counts["updated"] += 1

        if dry_run:
            transaction.set_rollback(True)
        return counts


__all__ = ["DjangoPermissionCatalogRepository"]
