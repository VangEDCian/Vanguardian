from django.db import models


class Study(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    sponsor = models.CharField(max_length=255, null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    description = models.CharField(max_length=255, default="")
    is_active = models.BooleanField(default=True)

    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "study_study"
        managed = False
        default_permissions = ()
        permissions = (
            ("view_study_list", "Can view study list"),
            ("view_study_detail", "Can view study detail"),
            ("view_study_history", "Can view study audit history"),
            ("create_study", "Can create study"),
            ("update_study", "Can update study"),
            ("change_study_status", "Can activate or deactivate a study"),
            ("delete_study", "Can delete study"),
            ("search_study_by_name", "Can search studies by name"),
            ("filter_study_by_code", "Can filter studies by code"),
            ("filter_study_by_status", "Can filter studies by status"),
            ("view_study_field_code", "Can view study code field"),
            ("view_study_field_name", "Can view study name field"),
            ("view_study_field_sponsor", "Can view study sponsor field"),
            ("view_study_field_dates", "Can view study start/end date fields"),
            ("view_study_field_description", "Can view study description field"),
            ("update_study_field_code", "Can update study code field"),
            ("update_study_field_name", "Can update study name field"),
            ("update_study_field_sponsor", "Can update study sponsor field"),
            ("update_study_field_dates", "Can update study start/end date fields"),
            ("update_study_field_description", "Can update study description field"),
        )
        indexes = [
            models.Index(fields=["deleted", "is_active"], name="study_deleted_active_idx"),
            models.Index(fields=["deleted", "start_date"], name="study_deleted_start_idx"),
            models.Index(fields=["deleted", "end_date"], name="study_deleted_end_idx"),
        ]
        verbose_name = "study"
        verbose_name_plural = "studies"


class CrfTemplate(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    code = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
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


class CrfPageTemplate(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    code = models.CharField(max_length=64)
    title = models.CharField(max_length=255)
    order = models.IntegerField()

    crf_template = models.ForeignKey(
        CrfTemplate,
        on_delete=models.DO_NOTHING,
        db_column="crf_template_id",
        related_name="page_templates",
    )
    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "crf_pagetemplate"
        managed = False
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["crf_template", "code"],
                name="crf_pagetemplate_crf_template_code_uniq",
            )
        ]
        verbose_name = "CRF page template"
        verbose_name_plural = "CRF page templates"


class CrfFieldTemplate(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    field_key = models.CharField(max_length=100)
    label = models.TextField()
    data_type = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    page_template = models.ForeignKey(
        CrfPageTemplate,
        on_delete=models.DO_NOTHING,
        db_column="page_template_id",
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
                fields=["page_template", "field_key"],
                name="crf_fieldtemplate_page_fieldkey_uniq",
            )
        ]
        verbose_name = "CRF field template"
        verbose_name_plural = "CRF field templates"


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
    codelist = models.TextField(default="", blank=True)
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


class CrfFieldValidationRule(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    rule_type = models.CharField(max_length=64)
    expression = models.TextField()
    message = models.TextField()
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
