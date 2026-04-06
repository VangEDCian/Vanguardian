from django.db import models

from .study import Study


class EventDefinition(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    study = models.ForeignKey(
        Study,
        on_delete=models.DO_NOTHING,
        db_column="study_id",
        related_name="event_definitions",
    )
    study_version_id = models.BigIntegerField()

    code = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    event_type = models.CharField(max_length=32)
    timing_mode = models.CharField(max_length=32, default="scheduled")

    sequence_no = models.IntegerField(default=1)
    phase_code = models.CharField(max_length=64, null=True, blank=True)

    is_repeating = models.BooleanField(default=False)
    max_repeats = models.IntegerField(null=True, blank=True)

    is_enabled = models.BooleanField(default=True)
    is_required = models.BooleanField(default=False)

    anchor_event_code = models.CharField(max_length=64, null=True, blank=True)
    day_offset = models.IntegerField(null=True, blank=True)
    window_before_days = models.IntegerField(null=True, blank=True)
    window_after_days = models.IntegerField(null=True, blank=True)

    opens_after_status = models.CharField(max_length=64, null=True, blank=True)

    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "study_eventdefinition"
        managed = False
        default_permissions = ()
        permissions = (
            ("view_study_eventdefinition_list", "Can view study event definition list"),
            ("create_study_eventdefinition", "Can create study event definition"),
            ("update_study_eventdefinition", "Can update study event definition"),
            ("delete_study_eventdefinition", "Can delete study event definition"),
        )
        constraints = [
            models.UniqueConstraint(
                fields=["study_version_id", "code"],
                name="study_evtdef_ver_code_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=["study", "study_version_id", "sequence_no"],
                name="study_evtdef_studyver_seq_idx",
            )
        ]
        verbose_name = "study event definition"
        verbose_name_plural = "study event definitions"
