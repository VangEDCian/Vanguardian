from django.core.management.base import BaseCommand

from apps.identity.management.commands.seed_permission import seed_permissions


class Command(BaseCommand):
    help = "Seed project-managed data. Usage: manage.py seed permission."

    def add_arguments(self, parser):
        parser.add_argument("target", choices=("permission",))
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be seeded without writing to the database.",
        )

    def handle(self, *args, **options):
        target = options["target"]
        if target == "permission":
            summary = seed_permissions(dry_run=options["dry_run"])
            self.stdout.write(self.style.SUCCESS(summary.message))
