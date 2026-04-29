from django.db import models


class DataCapturePageState(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    status = models.CharField(max_length=16)
    final_data = models.TextField()
    verified_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)

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
    verified_by_id = models.BigIntegerField(null=True, blank=True)
    locked_by_id = models.BigIntegerField(null=True, blank=True)

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

    entry_no = models.IntegerField()
    entry_kind = models.CharField(max_length=16)
    entry_version = models.CharField(max_length=16)
    data = models.TextField()
    status = models.CharField(max_length=16)

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

    class Meta:
        db_table = "datacapture_pageentry"
        managed = False
        default_permissions = ()
        indexes = [
            models.Index(
                fields=["subject", "visit", "crf_template", "entry_version"],
                name="datacapture_pageentry_subject_visit_crf_version_idx",
            )
        ]
        verbose_name = "data capture page entry"
        verbose_name_plural = "data capture page entries"


__all__ = [
    "DataCapturePageEntry",
    "DataCapturePageState",
]
