from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="Study",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("created_at", models.DateTimeField()),
                        ("updated_at", models.DateTimeField()),
                        ("deleted", models.BooleanField(default=False)),
                        ("code", models.CharField(max_length=64, unique=True)),
                        ("name", models.CharField(max_length=255)),
                        ("sponsor", models.CharField(max_length=255)),
                        ("start_date", models.DateField(blank=True, null=True)),
                        ("end_date", models.DateField(blank=True, null=True)),
                        ("description", models.TextField(default="")),
                        ("is_active", models.BooleanField(default=True)),
                        ("created_by_id", models.BigIntegerField(blank=True, null=True)),
                        ("updated_by_id", models.BigIntegerField(blank=True, null=True)),
                    ],
                    options={
                        "verbose_name": "study",
                        "verbose_name_plural": "studies",
                        "db_table": "study_study",
                        "managed": False,
                        "default_permissions": (),
                        "permissions": (
                            ("view_study_list", "Can view study list"),
                            ("view_study_detail", "Can view study detail"),
                            ("view_study_history", "Can view study audit history"),
                            ("create_study", "Can create study"),
                            ("update_study", "Can update study"),
                            ("change_study_status", "Can activate or deactivate a study"),
                            ("delete_study", "Can delete study"),
                            ("search_study_by_name", "Can search studies by name"),
                            ("filter_study_by_code", "Can filter studies by code"),
                            ("filter_study_by_status", "Can filter studies by status"),
                            ("view_study_field_code", "Can view study code field"),
                            ("view_study_field_name", "Can view study name field"),
                            ("view_study_field_sponsor", "Can view study sponsor field"),
                            ("view_study_field_dates", "Can view study start/end date fields"),
                            ("view_study_field_description", "Can view study description field"),
                            ("update_study_field_code", "Can update study code field"),
                            ("update_study_field_name", "Can update study name field"),
                            ("update_study_field_sponsor", "Can update study sponsor field"),
                            ("update_study_field_dates", "Can update study start/end date fields"),
                            ("update_study_field_description", "Can update study description field"),
                        ),
                        "indexes": [
                            models.Index(fields=["deleted", "is_active"], name="study_deleted_active_idx"),
                            models.Index(fields=["deleted", "start_date"], name="study_deleted_start_idx"),
                            models.Index(fields=["deleted", "end_date"], name="study_deleted_end_idx"),
                        ],
                    },
                ),
            ],
        ),
    ]
