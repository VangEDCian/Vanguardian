import django.db.models.deletion
import parler.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crf", "0001_crf_state"),
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
                migrations.CreateModel(
                    name="CrfTemplate",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("created_at", models.DateTimeField()),
                        ("updated_at", models.DateTimeField()),
                        ("deleted", models.BooleanField(default=False)),
                        ("code", models.CharField(max_length=64)),
                        ("version", models.CharField(max_length=32)),
                        ("is_active", models.BooleanField(default=True)),
                        ("created_by_id", models.BigIntegerField(blank=True, null=True)),
                        ("updated_by_id", models.BigIntegerField(blank=True, null=True)),
                        ("study", models.ForeignKey(
                            db_column="study_id",
                            on_delete=django.db.models.deletion.DO_NOTHING,
                            related_name="crf_templates",
                            to="study.study",
                        )),
                    ],
                    options={
                        "verbose_name": "CRF template",
                        "verbose_name_plural": "CRF templates",
                        "db_table": "crf_crftemplate",
                        "managed": False,
                        "default_permissions": (),
                        "constraints": [
                            models.UniqueConstraint(
                                fields=("study", "code", "version"),
                                name="crf_crftemplate_study_code_version_uniq",
                            )
                        ],
                    },
                    bases=(parler.models.TranslatableModel,),
                ),
                migrations.CreateModel(
                    name="CrfTemplateTranslation",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("name", models.CharField(max_length=255)),
                        ("master", models.ForeignKey(
                            db_column="crf_template_id",
                            on_delete=django.db.models.deletion.DO_NOTHING,
                            related_name="translations",
                            to="crf.crftemplate",
                        )),
                    ],
                    options={
                        "verbose_name": "CRF template translation",
                        "verbose_name_plural": "CRF template translations",
                        "db_table": "crf_crftemplate_translation",
                        "managed": False,
                        "default_permissions": (),
                        "indexes": [
                            models.Index(fields=["master"], name="crf_crftemplate_translation_master_idx"),
                            models.Index(fields=["language_code"], name="crf_crftemplate_translation_language_idx"),
                        ],
                        "constraints": [
                            models.UniqueConstraint(
                                fields=("language_code", "master"),
                                name="crf_crftemplate_translation_lang_template_uniq",
                            )
                        ],
                    },
                    bases=(parler.models.TranslatedFieldsModel,),
                ),
                migrations.CreateModel(
                    name="CrfPageTemplate",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("created_at", models.DateTimeField()),
                        ("updated_at", models.DateTimeField()),
                        ("deleted", models.BooleanField(default=False)),
                        ("code", models.CharField(max_length=64)),
                        ("order", models.IntegerField()),
                        ("created_by_id", models.BigIntegerField(blank=True, null=True)),
                        ("updated_by_id", models.BigIntegerField(blank=True, null=True)),
                        ("crf_template", models.ForeignKey(
                            db_column="crf_template_id",
                            on_delete=django.db.models.deletion.DO_NOTHING,
                            related_name="page_templates",
                            to="crf.crftemplate",
                        )),
                    ],
                    options={
                        "verbose_name": "CRF page template",
                        "verbose_name_plural": "CRF page templates",
                        "db_table": "crf_pagetemplate",
                        "managed": False,
                        "default_permissions": (),
                        "constraints": [
                            models.UniqueConstraint(
                                fields=("crf_template", "code"),
                                name="crf_pagetemplate_crf_template_code_uniq",
                            )
                        ],
                    },
                    bases=(parler.models.TranslatableModel,),
                ),
                migrations.CreateModel(
                    name="CrfPageTemplateTranslation",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("title", models.CharField(max_length=255)),
                        ("master", models.ForeignKey(
                            db_column="page_template_id",
                            on_delete=django.db.models.deletion.DO_NOTHING,
                            related_name="translations",
                            to="crf.crfpagetemplate",
                        )),
                    ],
                    options={
                        "verbose_name": "CRF page template translation",
                        "verbose_name_plural": "CRF page template translations",
                        "db_table": "crf_pagetemplate_translation",
                        "managed": False,
                        "default_permissions": (),
                        "indexes": [
                            models.Index(fields=["master"], name="crf_pagetemplate_translation_master_idx"),
                            models.Index(fields=["language_code"], name="crf_pagetemplate_translation_language_idx"),
                        ],
                        "constraints": [
                            models.UniqueConstraint(
                                fields=("language_code", "master"),
                                name="crf_pagetemplate_translation_lang_page_uniq",
                            )
                        ],
                    },
                    bases=(parler.models.TranslatedFieldsModel,),
                ),
                migrations.CreateModel(
                    name="CrfFieldTemplate",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("created_at", models.DateTimeField()),
                        ("updated_at", models.DateTimeField()),
                        ("deleted", models.BooleanField(default=False)),
                        ("field_key", models.CharField(max_length=100)),
                        ("data_type", models.CharField(max_length=20)),
                        ("is_active", models.BooleanField(default=True)),
                        ("created_by_id", models.BigIntegerField(blank=True, null=True)),
                        ("updated_by_id", models.BigIntegerField(blank=True, null=True)),
                        ("page_template", models.ForeignKey(
                            db_column="page_template_id",
                            on_delete=django.db.models.deletion.DO_NOTHING,
                            related_name="field_templates",
                            to="crf.crfpagetemplate",
                        )),
                    ],
                    options={
                        "verbose_name": "CRF field template",
                        "verbose_name_plural": "CRF field templates",
                        "db_table": "crf_fieldtemplate",
                        "managed": False,
                        "default_permissions": (),
                        "constraints": [
                            models.UniqueConstraint(
                                fields=("page_template", "field_key"),
                                name="crf_fieldtemplate_page_fieldkey_uniq",
                            )
                        ],
                    },
                    bases=(parler.models.TranslatableModel,),
                ),
                migrations.CreateModel(
                    name="CrfFieldTemplateTranslation",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("label", models.TextField()),
                        ("master", models.ForeignKey(
                            db_column="field_template_id",
                            on_delete=django.db.models.deletion.DO_NOTHING,
                            related_name="translations",
                            to="crf.crffieldtemplate",
                        )),
                    ],
                    options={
                        "verbose_name": "CRF field template translation",
                        "verbose_name_plural": "CRF field template translations",
                        "db_table": "crf_fieldtemplate_translation",
                        "managed": False,
                        "default_permissions": (),
                        "indexes": [
                            models.Index(fields=["master"], name="crf_fieldtemplate_translation_master_idx"),
                            models.Index(fields=["language_code"], name="crf_fieldtemplate_translation_language_idx"),
                        ],
                        "constraints": [
                            models.UniqueConstraint(
                                fields=("language_code", "master"),
                                name="crf_fieldtemplate_translation_lang_field_uniq",
                            )
                        ],
                    },
                    bases=(parler.models.TranslatedFieldsModel,),
                ),
                migrations.CreateModel(
                    name="CrfFieldDefinition",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("created_at", models.DateTimeField()),
                        ("updated_at", models.DateTimeField()),
                        ("deleted", models.BooleanField(default=False)),
                        ("sdtm", models.TextField(blank=True, null=True)),
                        ("unit", models.CharField(blank=True, max_length=50, null=True)),
                        ("range_min", models.DecimalField(blank=True, decimal_places=6, max_digits=21, null=True)),
                        ("range_max", models.DecimalField(blank=True, decimal_places=6, max_digits=21, null=True)),
                        ("precision", models.IntegerField(blank=True, null=True)),
                        ("allowed_missing_values", models.TextField(blank=True, default="")),
                        ("codelist", models.TextField(blank=True, default="")),
                        ("data_semantic", models.TextField(blank=True, null=True)),
                        ("comments", models.TextField(blank=True, null=True)),
                        ("text_max_length", models.IntegerField(blank=True, null=True)),
                        ("text_min_length", models.IntegerField(blank=True, null=True)),
                        ("pattern", models.TextField(blank=True, null=True)),
                        ("pattern_err_msg", models.TextField(blank=True, null=True)),
                        ("created_by_id", models.BigIntegerField(blank=True, null=True)),
                        ("updated_by_id", models.BigIntegerField(blank=True, null=True)),
                        ("field_template", models.OneToOneField(
                            db_column="field_template_id",
                            on_delete=django.db.models.deletion.DO_NOTHING,
                            related_name="definition",
                            to="crf.crffieldtemplate",
                        )),
                    ],
                    options={
                        "verbose_name": "CRF field definition",
                        "verbose_name_plural": "CRF field definitions",
                        "db_table": "crf_fielddefinition",
                        "managed": False,
                        "default_permissions": (),
                    },
                ),
                migrations.CreateModel(
                    name="CrfFieldUiConfig",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("created_at", models.DateTimeField()),
                        ("updated_at", models.DateTimeField()),
                        ("deleted", models.BooleanField(default=False)),
                        ("control_type", models.CharField(max_length=50)),
                        ("layout", models.TextField(blank=True, null=True)),
                        ("text", models.TextField(blank=True, null=True)),
                        ("behavior", models.TextField(blank=True, null=True)),
                        ("options", models.TextField(blank=True, null=True)),
                        ("style", models.TextField(blank=True, null=True)),
                        ("created_by_id", models.BigIntegerField(blank=True, null=True)),
                        ("updated_by_id", models.BigIntegerField(blank=True, null=True)),
                        ("field_template", models.OneToOneField(
                            db_column="field_template_id",
                            on_delete=django.db.models.deletion.DO_NOTHING,
                            related_name="ui_config",
                            to="crf.crffieldtemplate",
                        )),
                    ],
                    options={
                        "verbose_name": "CRF field UI config",
                        "verbose_name_plural": "CRF field UI configs",
                        "db_table": "crf_fielduiconfig",
                        "managed": False,
                        "default_permissions": (),
                    },
                ),
                migrations.CreateModel(
                    name="CrfFieldValidationRule",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("created_at", models.DateTimeField()),
                        ("updated_at", models.DateTimeField()),
                        ("deleted", models.BooleanField(default=False)),
                        ("rule_type", models.CharField(max_length=64)),
                        ("expression", models.TextField()),
                        ("severity", models.CharField(max_length=20)),
                        ("mode", models.CharField(max_length=20)),
                        ("created_by_id", models.BigIntegerField(blank=True, null=True)),
                        ("updated_by_id", models.BigIntegerField(blank=True, null=True)),
                        ("field_template", models.ForeignKey(
                            db_column="field_template_id",
                            on_delete=django.db.models.deletion.DO_NOTHING,
                            related_name="validation_rules",
                            to="crf.crffieldtemplate",
                        )),
                    ],
                    options={
                        "verbose_name": "CRF field validation rule",
                        "verbose_name_plural": "CRF field validation rules",
                        "db_table": "crf_fieldvalidationrule",
                        "managed": False,
                        "default_permissions": (),
                    },
                    bases=(parler.models.TranslatableModel,),
                ),
                migrations.CreateModel(
                    name="CrfFieldValidationRuleTranslation",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("message", models.TextField()),
                        ("master", models.ForeignKey(
                            db_column="field_validation_rule_id",
                            on_delete=django.db.models.deletion.DO_NOTHING,
                            related_name="translations",
                            to="crf.crffieldvalidationrule",
                        )),
                    ],
                    options={
                        "verbose_name": "CRF field validation rule translation",
                        "verbose_name_plural": "CRF field validation rule translations",
                        "db_table": "crf_fieldvalidationrule_translation",
                        "managed": False,
                        "default_permissions": (),
                        "indexes": [
                            models.Index(fields=["master"], name="crf_fieldvalidationrule_translation_master_idx"),
                            models.Index(fields=["language_code"], name="crf_fieldvalidationrule_translation_language_idx"),
                        ],
                        "constraints": [
                            models.UniqueConstraint(
                                fields=("language_code", "master"),
                                name="crf_fieldvalidationrule_translation_lang_rule_uniq",
                            )
                        ],
                    },
                    bases=(parler.models.TranslatedFieldsModel,),
                ),
            ],
        ),
    ]
