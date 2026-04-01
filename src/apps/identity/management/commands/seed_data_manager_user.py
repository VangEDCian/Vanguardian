"""
Management command: seed_data_manager_user

Creates a test Data Manager user and assigns the correct permissions
(view_study_list, view_study_detail, view_study_history, update_study)
directly to user_permissions so that has_perm() resolves correctly.

Also creates a StudyMembership for each active study so the data-scope
filter in StudyDirectoryQueryService returns records for this user.

Usage:
    python manage.py seed_data_manager_user
    python manage.py seed_data_manager_user --username dm_test --password secret123
    python manage.py seed_data_manager_user --no-membership
"""

import datetime

from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand

DATA_MANAGER_CODENAMES = [
    "view_study_list",
    "view_study_detail",
    "view_study_history",
    "update_study",
    "search_study_by_name",
    "filter_study_by_code",
    "filter_study_by_status",
    "view_study_field_code",
    "view_study_field_name",
    "view_study_field_sponsor",
    "view_study_field_dates",
    "view_study_field_description",
    # update_study_field_code excluded — Data Manager cannot change study code
    "update_study_field_name",
    "update_study_field_sponsor",
    "update_study_field_dates",
    "update_study_field_description",
]

DATA_MANAGER_ROLE = "Data Manager"


class Command(BaseCommand):
    help = "Seed a Data Manager test user with correct study permissions."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="data_manager", help="Username (default: data_manager)")
        parser.add_argument("--password", default="password123", help="Password (default: password123)")
        parser.add_argument("--email", default="dm@vanguardian.local", help="Email")
        parser.add_argument(
            "--no-membership",
            action="store_true",
            help="Skip creating StudyMembership records",
        )

    def handle(self, *args, **options):
        from apps.identity.infrastructure.persistence.models import StudyMembership, User
        from apps.study.infrastructure.persistence.models import Study

        username = options["username"]
        password = options["password"]
        email = options["email"]
        now = datetime.datetime.now()

        # ── 1. Create or update user ──────────────────────────────────────────
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "display_name": "Data Manager (test)"},
        )
        user.set_password(password)
        user.is_active = True
        user.is_staff = False
        user.is_superuser = False
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(f"{action} user: {username}")

        # ── 2. Assign permissions directly to user_permissions ────────────────
        perms = Permission.objects.filter(
            codename__in=DATA_MANAGER_CODENAMES,
            content_type__app_label="study",
        )
        found_codenames = set(perms.values_list("codename", flat=True))
        missing = set(DATA_MANAGER_CODENAMES) - found_codenames
        if missing:
            self.stdout.write(
                self.style.WARNING(
                    f"  WARNING: permissions not found (run migrate first): {missing}"
                )
            )

        user.user_permissions.set(perms)
        self.stdout.write(
            self.style.SUCCESS(f"  Assigned permissions: {sorted(found_codenames)}")
        )

        # ── 3. Create StudyMembership for all non-deleted studies ─────────────
        if not options["no_membership"]:
            studies = Study.objects.filter(deleted=False)
            count = 0
            for study in studies:
                _, mb_created = StudyMembership.objects.get_or_create(
                    user=user,
                    study_id=study.pk,
                    defaults={
                        "role": DATA_MANAGER_ROLE,
                        "is_global_role": True,
                        "deleted": False,
                        "created_at": now,
                        "updated_at": now,
                    },
                )
                if mb_created:
                    count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Created {count} StudyMembership(s) "
                    f"(total studies: {studies.count()})"
                )
            )
        else:
            self.stdout.write("  Skipped StudyMembership (--no-membership).")

        # ── Summary ───────────────────────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Done."))
        self.stdout.write(f"  Username : {username}")
        self.stdout.write(f"  Password : {password}")
        self.stdout.write(f"  Perms    : {', '.join(DATA_MANAGER_CODENAMES)}")
