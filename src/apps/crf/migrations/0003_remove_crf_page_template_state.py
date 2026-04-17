import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crf", "0002_crf_parler_state"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="crffieldtemplate",
                    name="crf_fieldtemplate_page_fieldkey_uniq",
                ),
                migrations.RenameField(
                    model_name="crffieldtemplate",
                    old_name="page_template",
                    new_name="crf_template",
                ),
                migrations.AlterField(
                    model_name="crffieldtemplate",
                    name="crf_template",
                    field=models.ForeignKey(
                        db_column="crf_template_id",
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="field_templates",
                        to="crf.crftemplate",
                    ),
                ),
                migrations.AddConstraint(
                    model_name="crffieldtemplate",
                    constraint=models.UniqueConstraint(
                        fields=("crf_template", "field_key"),
                        name="crf_fieldtemplate_crf_template_fieldkey_uniq",
                    ),
                ),
                migrations.DeleteModel(name="CrfPageTemplateTranslation"),
                migrations.DeleteModel(name="CrfPageTemplate"),
            ],
        )
    ]
