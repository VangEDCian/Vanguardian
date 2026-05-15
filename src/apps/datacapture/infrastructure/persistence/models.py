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
        managed = False
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["subject", "visit", "crf_template"],
                name="datacapture_pagestate_subject_visit_crf_uniq",
            )
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
        managed = False
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
        verbose_name = "data capture page entry"
        verbose_name_plural = "data capture page entries"


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
        managed = False
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["page_state", "field_template", "review_type", "data_version"],
                name="datacapture_fieldreview_page_field_type_uniq",
            )
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
        managed = False
        default_permissions = ()


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
        managed = False
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
    "DataCaptureFactMapping",
    "DataCapturePageEntry",
    "DataCapturePageState",
    "DataCapturePageStateTransitionLog",
]
