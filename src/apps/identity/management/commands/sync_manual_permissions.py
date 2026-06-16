from django.core.management.base import BaseCommand

from apps.identity.management.commands.seed_permission import seed_permissions


class Command(BaseCommand):
    help = "Deprecated alias: use `manage.py seed permission`."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be seeded without writing to the database.",
        )

    def handle(self, *args, **options):
        summary = seed_permissions(dry_run=options["dry_run"])
        self.stdout.write(
            self.style.WARNING(
                "Deprecated alias: use `manage.py seed permission`."
            )
        )
        self.stdout.write(self.style.SUCCESS(summary.message))
