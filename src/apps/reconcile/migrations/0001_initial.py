from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.CreateModel(
                    name="ReconcileDataQuery",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("created_at", models.DateTimeField()),
                        ("updated_at", models.DateTimeField()),
                        ("deleted", models.BooleanField(default=False)),
                        ("status", models.CharField(max_length=16)),
                        ("source", models.CharField(max_length=16)),
                        ("question_text", models.TextField()),
                        ("resolution_note", models.CharField(blank=True, max_length=255, null=True)),
                        ("closed_at", models.DateTimeField(blank=True, null=True)),
                        ("assigned_to_id", models.BigIntegerField(blank=True, null=True)),
                        ("created_by_id", models.BigIntegerField(blank=True, null=True)),
                        ("updated_by_id", models.BigIntegerField(blank=True, null=True)),
                        (
                            "field_template",
                            models.ForeignKey(
                                blank=True,
                                db_column="field_template_id",
                                null=True,
                                on_delete=models.deletion.DO_NOTHING,
                                related_name="reconcile_data_queries",
                                to="crf.crffieldtemplate",
                            ),
                        ),
                        (
                            "page_state",
                            models.ForeignKey(
                                db_column="page_state_id",
                                on_delete=models.deletion.DO_NOTHING,
                                related_name="reconcile_data_queries",
                                to="datacapture.datacapturepagestate",
                            ),
                        ),
                        (
                            "validation_rule",
                            models.ForeignKey(
                                blank=True,
                                db_column="validation_rule_id",
                                null=True,
                                on_delete=models.deletion.DO_NOTHING,
                                related_name="reconcile_data_queries",
                                to="crf.crffieldvalidationrule",
                            ),
                        ),
                    ],
                    options={
                        "db_table": "reconcile_dataquery",
                        "default_permissions": (),
                    },
                ),
            ],
            state_operations=[
                migrations.CreateModel(
                    name="ReconcileDataQuery",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("created_at", models.DateTimeField()),
                        ("updated_at", models.DateTimeField()),
                        ("deleted", models.BooleanField(default=False)),
                        ("status", models.CharField(max_length=16)),
                        ("source", models.CharField(max_length=16)),
                        ("question_text", models.TextField()),
                        ("resolution_note", models.CharField(blank=True, max_length=255, null=True)),
                        ("closed_at", models.DateTimeField(blank=True, null=True)),
                        ("assigned_to_id", models.BigIntegerField(blank=True, null=True)),
                        ("created_by_id", models.BigIntegerField(blank=True, null=True)),
                        ("updated_by_id", models.BigIntegerField(blank=True, null=True)),
                        (
                            "field_template",
                            models.ForeignKey(
                                blank=True,
                                db_column="field_template_id",
                                null=True,
                                on_delete=models.deletion.DO_NOTHING,
                                related_name="reconcile_data_queries",
                                to="crf.crffieldtemplate",
                            ),
                        ),
                        (
                            "page_state",
                            models.ForeignKey(
                                db_column="page_state_id",
                                on_delete=models.deletion.DO_NOTHING,
                                related_name="reconcile_data_queries",
                                to="datacapture.datacapturepagestate",
                            ),
                        ),
                        (
                            "validation_rule",
                            models.ForeignKey(
                                blank=True,
                                db_column="validation_rule_id",
                                null=True,
                                on_delete=models.deletion.DO_NOTHING,
                                related_name="reconcile_data_queries",
                                to="crf.crffieldvalidationrule",
                            ),
                        ),
                    ],
                    options={
                        "db_table": "reconcile_dataquery",
                        "managed": False,
                        "default_permissions": (),
                        "verbose_name": "reconcile data query",
                        "verbose_name_plural": "reconcile data queries",
                    },
                ),
            ],
        )
    ]

