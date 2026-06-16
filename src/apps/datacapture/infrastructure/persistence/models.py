from django.db import models

from apps.core.choices import (
    DataCapturePageEntryStatusChoices,
    DataCapturePageStateStatusChoices,
)


class DataCapturePageState(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    status = models.CharField(max_length=32, choices=DataCapturePageStateStatusChoices.choices)
    final_data = models.TextField(default="{}")

    data_version = models.IntegerField(default=1)
    current_entry = models.ForeignKey(
        "datacapture.DataCapturePageEntry",
        on_delete=models.DO_NOTHING,
        db_column="current_entry_id",
        related_name="current_for_page_states",
        null=True,
        blank=True,
    )

    submitted_at = models.DateTimeField(null=True, blank=True)
    review_started_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    verified_data_version = models.IntegerField(null=True, blank=True)
    locked_data_version = models.IntegerField(null=True, blank=True)
    finalized_data_version = models.IntegerField(null=True, blank=True)

    crf_template = models.ForeignKey(
        "crf.CrfTemplate",
        on_delete=models.DO_NOTHING,
        db_column="crf_template_id",
        related_name="data_capture_page_states",
    )
    subject = models.ForeignKey(
        "subject.Subject",
        on_delete=models.DO_NOTHING,
        db_column="subject_id",
        related_name="data_capture_page_states",
    )
    visit = models.ForeignKey(
        "subject.SubjectEventInstance",
        on_delete=models.DO_NOTHING,
        db_column="visit_id",
        related_name="data_capture_page_states",
    )

    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)
    submitted_by_id = models.BigIntegerField(null=True, blank=True)
    review_started_by_id = models.BigIntegerField(null=True, blank=True)
    verified_by_id = models.BigIntegerField(null=True, blank=True)
    locked_by_id = models.BigIntegerField(null=True, blank=True)
    finalized_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "datacapture_pagestate"
        managed = True
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["subject", "visit", "crf_template"],
                name="datacapture_pagestate_subject_visit_crf_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["subject", "status"], name="dcps_subject_status_idx"),
            models.Index(fields=["visit", "status"], name="dcps_visit_status_idx"),
            models.Index(fields=["crf_template", "status"], name="dcps_crf_status_idx"),
        ]
        verbose_name = "data capture page state"
        verbose_name_plural = "data capture page states"


class DataCapturePageEntry(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    page_state = models.ForeignKey(
        DataCapturePageState,
        on_delete=models.DO_NOTHING,
        db_column="page_state_id",
        related_name="page_entries",
    )
    parent_entry = models.ForeignKey(
        "self",
        on_delete=models.DO_NOTHING,
        db_column="parent_entry_id",
        related_name="correction_entries",
        null=True,
        blank=True,
    )

    entry_no = models.IntegerField()
    entry_kind = models.CharField(max_length=16)
    entry_version = models.CharField(max_length=16)
    data = models.TextField()
    status = models.CharField(max_length=32, choices=DataCapturePageEntryStatusChoices.choices)

    submitted_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)

    rejection_reason = models.TextField(null=True, blank=True)
    correction_reason = models.TextField(null=True, blank=True)

    crf_template = models.ForeignKey(
        "crf.CrfTemplate",
        on_delete=models.DO_NOTHING,
        db_column="crf_template_id",
        related_name="data_capture_page_entries",
    )
    subject = models.ForeignKey(
        "subject.Subject",
        on_delete=models.DO_NOTHING,
        db_column="subject_id",
        related_name="data_capture_page_entries",
    )
    visit = models.ForeignKey(
        "subject.SubjectEventInstance",
        on_delete=models.DO_NOTHING,
        db_column="visit_id",
        related_name="data_capture_page_entries",
    )

    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)
    submitted_by_id = models.BigIntegerField(null=True, blank=True)
    accepted_by_id = models.BigIntegerField(null=True, blank=True)
    rejected_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "datacapture_pageentry"
        managed = True
        default_permissions = ()
        indexes = [
            models.Index(
                fields=["subject", "visit", "crf_template", "entry_version"],
                name="dcpg_sub_vis_crf_ver_idx",
            ),
            models.Index(
                fields=["page_state", "status"],
                name="dcpg_pagestate_status_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["page_state", "entry_version"],
                name="dcpe_pagestate_version_uniq",
            )
        ]
        verbose_name = "data capture page entry"
        verbose_name_plural = "data capture page entries"


class DataCaptureSectionInstance(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    page_entry = models.ForeignKey(
        DataCapturePageEntry,
        on_delete=models.DO_NOTHING,
        db_column="page_entry_id",
        related_name="section_instances",
    )
    page_state = models.ForeignKey(
        DataCapturePageState,
        on_delete=models.DO_NOTHING,
        db_column="page_state_id",
        related_name="section_instances",
    )
    section_template = models.ForeignKey(
        "crf.CrfSectionTemplate",
        on_delete=models.DO_NOTHING,
        db_column="section_template_id",
        related_name="data_capture_section_instances",
    )

    repeat_index = models.IntegerField(default=1)
    instance_key = models.CharField(max_length=64)
    status = models.CharField(max_length=16, default="active")

    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "datacapture_sectioninstance"
        managed = True
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["page_entry", "section_template", "repeat_index"],
                name="dcsi_entry_section_repeat_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=["page_state", "section_template", "repeat_index"],
                name="dcsi_state_section_repeat_idx",
            ),
        ]
        verbose_name = "data capture section instance"
        verbose_name_plural = "data capture section instances"


class DataCaptureFieldEntry(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    page_entry = models.ForeignKey(
        DataCapturePageEntry,
        on_delete=models.DO_NOTHING,
        db_column="page_entry_id",
        related_name="field_entries",
    )
    page_state = models.ForeignKey(
        DataCapturePageState,
        on_delete=models.DO_NOTHING,
        db_column="page_state_id",
        related_name="field_entries",
    )
    section_instance = models.ForeignKey(
        DataCaptureSectionInstance,
        on_delete=models.DO_NOTHING,
        db_column="section_instance_id",
        related_name="field_entries",
        null=True,
        blank=True,
    )
    field_template = models.ForeignKey(
        "crf.CrfFieldTemplate",
        on_delete=models.DO_NOTHING,
        db_column="field_template_id",
        related_name="data_capture_field_entries",
    )

    value_text = models.TextField(null=True, blank=True)
    value_json = models.TextField(null=True, blank=True)
    value_date = models.DateField(null=True, blank=True)
    value_number = models.DecimalField(max_digits=21, decimal_places=6, null=True, blank=True)
    value_bool = models.BooleanField(null=True, blank=True)

    status = models.CharField(max_length=16, default="active")

    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "datacapture_fieldentry"
        managed = True
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["page_entry", "section_instance", "field_template"],
                name="dcfe_entry_section_field_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["page_state", "field_template"], name="dcfe_state_field_idx"),
            models.Index(fields=["section_instance"], name="dcfe_section_instance_idx"),
        ]
        verbose_name = "data capture field entry"
        verbose_name_plural = "data capture field entries"


class DataCaptureFieldReview(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    page_state = models.ForeignKey(
        DataCapturePageState,
        on_delete=models.DO_NOTHING,
        db_column="page_state_id",
        related_name="field_reviews",
    )
    field_template = models.ForeignKey(
        "crf.CrfFieldTemplate",
        on_delete=models.DO_NOTHING,
        db_column="field_template_id",
        related_name="data_capture_field_reviews",
    )

    review_type = models.CharField(max_length=32)
    status = models.CharField(max_length=32)
    data_version = models.IntegerField()
    value_snapshot = models.TextField(null=True, blank=True)

    reviewed_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    reason_code = models.CharField(max_length=64, null=True, blank=True)
    reason_text = models.TextField(null=True, blank=True)

    reviewed_by_id = models.BigIntegerField(null=True, blank=True)
    verified_by_id = models.BigIntegerField(null=True, blank=True)
    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "datacapture_fieldreview"
        managed = True
        default_permissions = ()
        indexes = [
            models.Index(fields=["page_state", "status"], name="dcfr_page_status_idx"),
            models.Index(fields=["field_template", "status"], name="dcfr_field_status_idx"),
            models.Index(fields=["page_state", "data_version"], name="dcfr_page_version_idx"),
        ]


class DataCapturePageStateTransitionLog(models.Model):
    created_at = models.DateTimeField()

    page_state = models.ForeignKey(
        DataCapturePageState,
        on_delete=models.DO_NOTHING,
        db_column="page_state_id",
        related_name="transition_logs",
    )

    from_status = models.CharField(max_length=32, null=True, blank=True)
    to_status = models.CharField(max_length=32)

    data_version = models.IntegerField(null=True, blank=True)
    reason_code = models.CharField(max_length=64, null=True, blank=True)
    reason_text = models.TextField(null=True, blank=True)

    trigger_source = models.CharField(max_length=32)
    actor_id = models.BigIntegerField(null=True, blank=True)
    facts_json = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "datacapture_pagestate_transition_log"
        managed = True
        default_permissions = ()
        indexes = [
            models.Index(fields=["page_state", "created_at"], name="dcps_trlog_page_time_idx"),
            models.Index(fields=["page_state", "to_status"], name="dcps_trlog_page_status_idx"),
        ]


class DataCaptureFactMapping(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    study = models.ForeignKey(
        "study.Study",
        on_delete=models.DO_NOTHING,
        db_column="study_id",
        related_name="data_capture_fact_mappings",
    )
    study_version = models.CharField(max_length=20)
    crf_template = models.ForeignKey(
        "crf.CrfTemplate",
        on_delete=models.DO_NOTHING,
        db_column="crf_template_id",
        related_name="data_capture_fact_mappings",
    )
    event_definition = models.ForeignKey(
        "study.EventDefinition",
        on_delete=models.DO_NOTHING,
        db_column="event_definition_id",
        related_name="data_capture_fact_mappings",
        null=True,
        blank=True,
    )

    field_code = models.CharField(max_length=128, null=True, blank=True)
    source_path = models.CharField(max_length=512)
    fact_key = models.CharField(max_length=128)
    operator = models.CharField(max_length=32, default="equals")
    expected_value = models.TextField(null=True, blank=True)
    value_type = models.CharField(max_length=32, default="string")
    default_value = models.TextField(null=True, blank=True)

    is_enabled = models.BooleanField(default=True)
    display_order = models.IntegerField(default=1)

    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "datacapture_fact_mapping"
        managed = True
        default_permissions = ()
        indexes = [
            models.Index(
                fields=["study", "study_version", "crf_template", "is_enabled"],
                name="datacapture_fact_map_scope_idx",
            ),
            models.Index(
                fields=["event_definition", "is_enabled"],
                name="datacapture_fact_map_event_idx",
            ),
            models.Index(
                fields=["crf_template", "fact_key"],
                name="dcfm_tpl_fact_idx",
            ),
        ]
        verbose_name = "data capture fact mapping"
        verbose_name_plural = "data capture fact mappings"


__all__ = [
    "DataCaptureFieldReview",
    "DataCaptureFieldEntry",
    "DataCaptureFactMapping",
    "DataCapturePageEntry",
    "DataCapturePageState",
    "DataCapturePageStateTransitionLog",
    "DataCaptureSectionInstance",
]
