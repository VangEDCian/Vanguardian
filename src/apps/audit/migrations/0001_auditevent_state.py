# fmt: off
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("identity", "0004_membership_state"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="AuditEvent",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("created_at", models.DateTimeField()),
                        ("updated_at", models.DateTimeField()),
                        ("deleted", models.BooleanField(default=False)),
                        ("action", models.CharField(max_length=64)),
                        ("object_type", models.CharField(max_length=64)),
                        ("object_id", models.CharField(max_length=64)),
                        ("before_data", models.TextField(default="{}")),
                        ("after_data", models.TextField(default="{}")),
                        ("ip_address", models.CharField(blank=True, max_length=39, null=True)),
                        ("user_agent", models.CharField(blank=True, default="", max_length=255)),
                        (
                            "created_by",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=models.deletion.DO_NOTHING,
                                related_name="created_audit_events",
                                to="identity.user",
                            ),
                        ),
                        (
                            "updated_by",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=models.deletion.DO_NOTHING,
                                related_name="updated_audit_events",
                                to="identity.user",
                            ),
                        ),
                        (
                            "user",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=models.deletion.DO_NOTHING,
                                related_name="audit_events",
                                to="identity.user",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "audit event",
                        "verbose_name_plural": "audit events",
                        "db_table": "audit_auditevent",
                        "managed": False,
                        "default_permissions": (),
                        "permissions": (),
                        "indexes": [
                            models.Index(
                                fields=["object_type", "object_id", "created_at"],
                                name="audit_auditevent_obj_time_idx",
                            )
                        ],
                    },
                ),
            ],
        ),
    ]
