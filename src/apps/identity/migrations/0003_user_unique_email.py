from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("identity", "0002_user_phone_number"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name="user",
                    name="email",
                    field=models.EmailField(
                        blank=True,
                        max_length=254,
                        null=True,
                        unique=True,
                        verbose_name="email address",
                    ),
                ),
            ],
        ),
    ]
