from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("crf", "0001_crf_state"),
        ("study", "0002_crf_state"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name="CrfFieldValidationRule"),
                migrations.DeleteModel(name="CrfFieldUiConfig"),
                migrations.DeleteModel(name="CrfFieldDefinition"),
                migrations.DeleteModel(name="CrfFieldTemplate"),
                migrations.DeleteModel(name="CrfPageTemplate"),
                migrations.DeleteModel(name="CrfTemplate"),
            ],
        ),
    ]
