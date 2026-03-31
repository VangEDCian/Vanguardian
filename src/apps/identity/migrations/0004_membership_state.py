from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("identity", "0003_user_unique_email"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="StudyMembership",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("study_id", models.BigIntegerField()),
                        ("deleted", models.BooleanField(default=False)),
                        ("user", models.ForeignKey(on_delete=models.deletion.DO_NOTHING, to="identity.user")),
                    ],
                    options={
                        "verbose_name": "study membership",
                        "verbose_name_plural": "study memberships",
                        "db_table": "study_membership",
                        "managed": False,
                        "default_permissions": (),
                        "permissions": (),
                        "unique_together": {("user", "study_id")},
                    },
                ),
                migrations.CreateModel(
                    name="StudySiteMembership",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("study_id", models.BigIntegerField()),
                        ("site_id", models.BigIntegerField()),
                        ("deleted", models.BooleanField(default=False)),
                        ("user", models.ForeignKey(on_delete=models.deletion.DO_NOTHING, to="identity.user")),
                    ],
                    options={
                        "verbose_name": "study site membership",
                        "verbose_name_plural": "study site memberships",
                        "db_table": "study_site_membership",
                        "managed": False,
                        "default_permissions": (),
                        "permissions": (),
                        "unique_together": {("user", "study_id", "site_id")},
                    },
                ),
            ],
        ),
    ]
