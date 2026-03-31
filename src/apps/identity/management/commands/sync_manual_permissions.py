from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = (
        "Deprecated: identity permissions are now created by Django migrate via "
        "Meta.permissions + django_content_type."
    )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING(
                "No-op: run `./manage.py migrate` to create/update permissions."
            )
        )
