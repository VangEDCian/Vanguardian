from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from apps.identity.infrastructure.auth.permissions import IDENTITY_PERMISSION_SPECS
from apps.identity.infrastructure.persistence.models import User


class Command(BaseCommand):
    help = (
        "Create or update the project's manually curated identity permissions. "
        "Run only for permission specs explicitly agreed by developers and business."
    )

    def handle(self, *args, **options):
        content_type = ContentType.objects.get_for_model(User)
        created_count = 0
        updated_count = 0

        for spec in IDENTITY_PERMISSION_SPECS:
            permission, created = Permission.objects.update_or_create(
                content_type=content_type,
                codename=spec.codename,
                defaults={"name": spec.name},
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Created permission {permission.codename}")
                )
            else:
                updated_count += 1
                self.stdout.write(f"Updated permission {permission.codename}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Permission sync complete: created={created_count}, updated={updated_count}"
            )
        )
