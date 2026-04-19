from django.db import models
from parler.fields import TranslatedField
from parler.models import TranslatableModel, TranslatedFieldsModel

from apps.study.models import Study


class CrfTemplate(TranslatableModel):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    code = models.CharField(max_length=64)
    name = TranslatedField(any_language=True)
    version = models.CharField(max_length=32)
    is_active = models.BooleanField(default=True)

    study = models.ForeignKey(
        Study,
        on_delete=models.DO_NOTHING,
        db_column="study_id",
        related_name="crf_templates",
    )
    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "crf_crftemplate"
        managed = False
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["study", "code", "version"],
                name="crf_crftemplate_study_code_version_uniq",
            )
        ]
        verbose_name = "CRF template"
        verbose_name_plural = "CRF templates"


class CrfTemplateTranslation(TranslatedFieldsModel):
    master = models.ForeignKey(
        CrfTemplate,
        on_delete=models.DO_NOTHING,
        db_column="crf_template_id",
        related_name="translations",
    )
    name = models.CharField(max_length=255)

    class Meta:
        db_table = "crf_crftemplate_translation"
        managed = False
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["language_code", "master"],
                name="crf_crftemplate_translation_lang_template_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["master"], name="crf_crftemplate_translation_master_idx"),
            models.Index(fields=["language_code"], name="crf_crftemplate_translation_language_idx"),
        ]
        verbose_name = "CRF template translation"
        verbose_name_plural = "CRF template translations"


class CrfFieldTemplate(TranslatableModel):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    field_key = models.CharField(max_length=100)
    label = TranslatedField(any_language=True)
    data_type = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    crf_template = models.ForeignKey(
        CrfTemplate,
        on_delete=models.DO_NOTHING,
        db_column="crf_template_id",
        related_name="field_templates",
    )
    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "crf_fieldtemplate"
        managed = False
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["crf_template", "field_key"],
                name="crf_fieldtemplate_crf_template_fieldkey_uniq",
            )
        ]
        verbose_name = "CRF field template"
        verbose_name_plural = "CRF field templates"


class CrfFieldTemplateTranslation(TranslatedFieldsModel):
    master = models.ForeignKey(
        CrfFieldTemplate,
        on_delete=models.DO_NOTHING,
        db_column="field_template_id",
        related_name="translations",
    )
    label = models.TextField()

    class Meta:
        db_table = "crf_fieldtemplate_translation"
        managed = False
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["language_code", "master"],
                name="crf_fieldtemplate_translation_lang_field_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["master"], name="crf_fieldtemplate_translation_master_idx"),
            models.Index(fields=["language_code"], name="crf_fieldtemplate_translation_language_idx"),
        ]
        verbose_name = "CRF field template translation"
        verbose_name_plural = "CRF field template translations"


class CrfFieldDefinition(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    sdtm = models.TextField(null=True, blank=True)
    unit = models.CharField(max_length=50, null=True, blank=True)
    range_min = models.DecimalField(max_digits=21, decimal_places=6, null=True, blank=True)
    range_max = models.DecimalField(max_digits=21, decimal_places=6, null=True, blank=True)
    precision = models.IntegerField(null=True, blank=True)
    allowed_missing_values = models.TextField(default="", blank=True)
    codelist = models.TextField(null=True, blank=True)
    data_semantic = models.TextField(null=True, blank=True)
    comments = models.TextField(null=True, blank=True)
    text_max_length = models.IntegerField(null=True, blank=True)
    text_min_length = models.IntegerField(null=True, blank=True)
    pattern = models.TextField(null=True, blank=True)
    pattern_err_msg = models.TextField(null=True, blank=True)

    field_template = models.OneToOneField(
        CrfFieldTemplate,
        on_delete=models.DO_NOTHING,
        db_column="field_template_id",
        related_name="definition",
    )
    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "crf_fielddefinition"
        managed = False
        default_permissions = ()
        verbose_name = "CRF field definition"
        verbose_name_plural = "CRF field definitions"


class CrfFieldUiConfig(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    control_type = models.CharField(max_length=50)
    layout = models.TextField(null=True, blank=True)
    text = models.TextField(null=True, blank=True)
    behavior = models.TextField(null=True, blank=True)
    options = models.TextField(null=True, blank=True)
    style = models.TextField(null=True, blank=True)

    field_template = models.OneToOneField(
        CrfFieldTemplate,
        on_delete=models.DO_NOTHING,
        db_column="field_template_id",
        related_name="ui_config",
    )
    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "crf_fielduiconfig"
        managed = False
        default_permissions = ()
        verbose_name = "CRF field UI config"
        verbose_name_plural = "CRF field UI configs"


class CrfFieldValidationRule(TranslatableModel):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    rule_type = models.CharField(max_length=64)
    expression = models.TextField()
    message = TranslatedField(any_language=True)
    severity = models.CharField(max_length=20)
    mode = models.CharField(max_length=20)

    field_template = models.ForeignKey(
        CrfFieldTemplate,
        on_delete=models.DO_NOTHING,
        db_column="field_template_id",
        related_name="validation_rules",
    )
    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "crf_fieldvalidationrule"
        managed = False
        default_permissions = ()
        verbose_name = "CRF field validation rule"
        verbose_name_plural = "CRF field validation rules"


class CrfFieldValidationRuleTranslation(TranslatedFieldsModel):
    master = models.ForeignKey(
        CrfFieldValidationRule,
        on_delete=models.DO_NOTHING,
        db_column="field_validation_rule_id",
        related_name="translations",
    )
    message = models.TextField()

    class Meta:
        db_table = "crf_fieldvalidationrule_translation"
        managed = False
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["language_code", "master"],
                name="crf_fieldvalidationrule_translation_lang_rule_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["master"], name="crf_fieldvalidationrule_translation_master_idx"),
            models.Index(fields=["language_code"], name="crf_fieldvalidationrule_translation_language_idx"),
        ]
        verbose_name = "CRF field validation rule translation"
        verbose_name_plural = "CRF field validation rule translations"
