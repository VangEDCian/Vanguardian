"""
Management command: seed_admin_user

Creates a test Administrator user with full study permissions including
change_study_status so the Deactivate/Activate button shows in study_detail.

Usage:
    python manage.py seed_admin_user
    python manage.py seed_admin_user --username admin_test --password secret123
"""

from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand

ADMIN_CODENAMES = [
    "view_study_list",
    "view_study_detail",
    "view_study_history",
    "create_study",
    "update_study",
    "change_study_status",
    "delete_study",
    "search_study_by_name",
    "filter_study_by_code",
    "filter_study_by_status",
    "view_study_field_code",
    "view_study_field_name",
    "view_study_field_sponsor",
    "view_study_field_dates",
    "view_study_field_description",
    "update_study_field_code",
    "update_study_field_name",
    "update_study_field_sponsor",
    "update_study_field_dates",
    "update_study_field_description",
]


class Command(BaseCommand):
    help = "Seed an Administrator test user with full study permissions."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin_test", help="Username (default: admin_test)")
        parser.add_argument("--password", default="password123", help="Password (default: password123)")
        parser.add_argument("--email", default="admin@vanguardian.local", help="Email")

    def handle(self, *args, **options):
        from apps.identity.infrastructure.persistence.models import User

        username = options["username"]
        password = options["password"]
        email = options["email"]

        # ── 1. Create or update user ──────────────────────────────────────────
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "display_name": "Administrator (test)"},
        )
        user.set_password(password)
        user.is_active = True
        user.is_staff = True
        user.is_superuser = False
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(f"{action} user: {username}")

        # ── 2. Assign permissions directly to user_permissions ────────────────
        perms = Permission.objects.filter(
            codename__in=ADMIN_CODENAMES,
            content_type__app_label="study",
        )
        found_codenames = set(perms.values_list("codename", flat=True))
        missing = set(ADMIN_CODENAMES) - found_codenames
        if missing:
            self.stdout.write(self.style.WARNING(f"  WARNING: permissions not found (run migrate first): {missing}"))

        user.user_permissions.set(perms)
        self.stdout.write(self.style.SUCCESS(f"  Assigned permissions: {sorted(found_codenames)}"))

        # ── Summary ───────────────────────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Done."))
        self.stdout.write(f"  Username : {username}")
        self.stdout.write(f"  Password : {password}")
        self.stdout.write(f"  Perms    : {', '.join(ADMIN_CODENAMES)}")
        self.stdout.write("  Note     : Can see Deactivate/Activate button in study_detail")
