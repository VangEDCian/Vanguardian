from django.db import migrations, models


def add_invalidate_on_query_change_if_missing(apps, schema_editor):
    table_name = "study_eventattestation_policy"
    existing_columns = {
        column.name
        for column in schema_editor.connection.introspection.get_table_description(
            schema_editor.connection.cursor(),
            table_name,
        )
    }
    if "invalidate_on_query_change" in existing_columns:
        return

    model = apps.get_model("study", "EventAttestationPolicy")
    field = models.BooleanField(default=True)
    field.set_attributes_from_name("invalidate_on_query_change")
    schema_editor.add_field(model, field)


class Migration(migrations.Migration):
    dependencies = [
        ("study", "0002_eventattestationpolicy_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    add_invalidate_on_query_change_if_missing,
                    reverse_code=migrations.RunPython.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="eventattestationpolicy",
                    name="invalidate_on_query_change",
                    field=models.BooleanField(default=True),
                ),
            ],
        ),
    ]
