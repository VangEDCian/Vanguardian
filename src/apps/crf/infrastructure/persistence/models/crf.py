from django.db import models
from django.utils.translation import gettext_lazy as _
from parler.fields import TranslatedField
from parler.models import TranslatableModel, TranslatedFieldsModel

from apps.study.models import Study


class CrfFieldControlTypeChoices(models.TextChoices):
    TEXT = "TEXT", _("Text")
    TEXTAREA = "TEXTAREA", _("Textarea")
    NUMBER = "NUMBER", _("Number")
    SELECT = "SELECT", _("Select")
    RADIO = "RADIO", _("Radio")
    CHECKBOX = "CHECKBOX", _("Checkbox")
    MULTI_SELECT = "MULTI_SELECT", _("Multi Select")
    DATE = "DATE", _("Date")
    DATETIME = "DATETIME", _("DateTime")
    LABEL_ONLY = "LABEL_ONLY", _("Label Only")


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
            models.Index(fields=["master"], name="crf_ct_tr_m_idx"),
            models.Index(fields=["language_code"], name="crf_ct_tr_l_idx"),
        ]
        verbose_name = "CRF template translation"
        verbose_name_plural = "CRF template translations"


class CrfSectionTemplate(TranslatableModel):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    section_code = models.CharField(max_length=64)
    section_name = TranslatedField(any_language=True)
    display_order = models.IntegerField(default=1)

    is_required = models.BooleanField(default=True)
    is_enabled = models.BooleanField(default=True)
    is_repeatable = models.BooleanField(default=False)
    min_repeats = models.IntegerField(default=0)
    max_repeats = models.IntegerField(null=True, blank=True)

    crf_template = models.ForeignKey(
        CrfTemplate,
        on_delete=models.DO_NOTHING,
        db_column="crf_template_id",
        related_name="section_templates",
    )
    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "crf_sectiontemplate"
        managed = False
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["crf_template", "section_code"],
                name="crf_sectiontemplate_crf_template_section_code_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=["crf_template", "display_order"],
                name="crf_st_ct_do_idx",
            )
        ]
        verbose_name = "CRF section template"
        verbose_name_plural = "CRF section templates"


class CrfSectionTemplateTranslation(TranslatedFieldsModel):
    master = models.ForeignKey(
        CrfSectionTemplate,
        on_delete=models.DO_NOTHING,
        db_column="section_template_id",
        related_name="translations",
    )
    section_name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    help_text = models.TextField(null=True, blank=True)
    instruction_text = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "crf_sectiontemplate_translation"
        managed = False
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["language_code", "master"],
                name="crf_sectiontemplate_translation_lang_section_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["master"], name="crf_st_tr_m_idx"),
            models.Index(fields=["language_code"], name="crf_st_tr_l_idx"),
        ]
        verbose_name = "CRF section template translation"
        verbose_name_plural = "CRF section template translations"


class CrfSectionLayoutConfig(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    layout_type = models.CharField(max_length=32, default="section")
    column_count = models.IntegerField(default=1)
    label_position = models.CharField(max_length=16, default="top")
    density = models.CharField(max_length=16, default="standard")
    section_style = models.CharField(max_length=32, default="plain")
    is_collapsible = models.BooleanField(default=False)
    is_expanded_by_default = models.BooleanField(default=True)
    show_section_header = models.BooleanField(default=True)
    show_border = models.BooleanField(default=False)
    show_background = models.BooleanField(default=False)
    custom_css_class = models.CharField(max_length=128, null=True, blank=True)
    custom_layout_schema = models.JSONField(null=True, blank=True)

    section_template = models.OneToOneField(
        CrfSectionTemplate,
        on_delete=models.DO_NOTHING,
        db_column="section_template_id",
        related_name="layout_config",
    )
    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "crf_section_layoutconfig"
        managed = False
        default_permissions = ()
        verbose_name = "CRF section layout config"
        verbose_name_plural = "CRF section layout configs"


class CrfFieldTemplate(TranslatableModel):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    field_key = models.CharField(max_length=100)
    label = TranslatedField(any_language=True)
    data_type = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=1)

    crf_template = models.ForeignKey(
        CrfTemplate,
        on_delete=models.DO_NOTHING,
        db_column="crf_template_id",
        related_name="field_templates",
    )
    section_template = models.ForeignKey(
        CrfSectionTemplate,
        on_delete=models.DO_NOTHING,
        db_column="section_template_id",
        related_name="field_templates",
        null=True,
        blank=True,
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
            models.Index(fields=["master"], name="crf_ft_tr_m_idx"),
            models.Index(fields=["language_code"], name="crf_ft_tr_l_idx"),
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

    control_type = models.CharField(
        max_length=50,
        choices=CrfFieldControlTypeChoices.choices,
    )
    control_layout = models.CharField(max_length=20, default="normal")
    layout = models.TextField(null=True, blank=True)
    text = models.TextField(null=True, blank=True)
    behavior = models.TextField(null=True, blank=True)
    options = models.TextField(null=True, blank=True)
    style = models.TextField(null=True, blank=True)
    classes = models.CharField(max_length=255, null=True, blank=True)

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
            models.Index(fields=["master"], name="crf_fvr_tr_m_idx"),
            models.Index(fields=["language_code"], name="crf_fvr_tr_l_idx"),
        ]
        verbose_name = "CRF field validation rule translation"
        verbose_name_plural = "CRF field validation rule translations"


class CrfFieldReviewPolicy(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    study = models.ForeignKey(
        "study.Study",
        on_delete=models.DO_NOTHING,
        db_column="study_id",
        related_name="crf_field_review_policies",
    )
    study_version = models.CharField(max_length=20)
    crf_template = models.ForeignKey(
        CrfTemplate,
        on_delete=models.DO_NOTHING,
        db_column="crf_template_id",
        related_name="field_review_policies",
    )
    field_template = models.ForeignKey(
        CrfFieldTemplate,
        on_delete=models.DO_NOTHING,
        db_column="field_template_id",
        related_name="review_policies",
    )

    review_type = models.CharField(max_length=32)
    is_required_for_page_verify = models.BooleanField(default=False)
    is_required_for_lock = models.BooleanField(default=False)
    is_blocking_if_missing = models.BooleanField(default=True)

    role_required = models.CharField(max_length=64, null=True, blank=True)
    is_enabled = models.BooleanField(default=True)

    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "crf_fieldreview_policy"
        managed = False
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["study", "study_version", "crf_template", "field_template", "review_type"],
                name="crf_fieldreview_policy_scope_uniq",
            )
        ]
        verbose_name = "CRF field review policy"
        verbose_name_plural = "CRF field review policies"
