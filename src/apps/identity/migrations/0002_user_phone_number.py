from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("identity", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name="user",
                    name="phone_number",
                    field=models.CharField(blank=True, max_length=32, null=True, unique=True),
                ),
            ],
        ),
    ]
