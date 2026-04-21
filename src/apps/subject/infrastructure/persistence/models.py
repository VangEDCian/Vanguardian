from django.db import models

from apps.study.infrastructure.persistence.models import EventDefinition, Site, Study


class Subject(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    subject_code = models.CharField(max_length=64, null=True, blank=True)
    screening_code = models.CharField(max_length=64, null=True, blank=True)
    current_sequence = models.BigIntegerField()

    site = models.ForeignKey(
        Site,
        on_delete=models.DO_NOTHING,
        db_column="site_id",
        related_name="subjects",
    )
    study = models.ForeignKey(
        Study,
        on_delete=models.DO_NOTHING,
        db_column="study_id",
        related_name="subjects",
    )
    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "study_subject"
        managed = False
        default_permissions = ()
        permissions = (
            ("view_subject_list", "Can view subject list"),
            ("view_subject_detail", "Can view subject detail"),
            ("create_subject", "Can create subject"),
            ("update_subject", "Can update subject"),
            ("delete_subject", "Can delete subject"),
        )
        constraints = [
            models.UniqueConstraint(
                fields=["study", "site", "subject_code"],
                name="study_subj_study_site_code_uq",
            ),
            models.UniqueConstraint(
                fields=["study", "screening_code"],
                name="study_subj_study_screening_code_uq",
            ),
            models.UniqueConstraint(
                fields=["study", "current_sequence"],
                name="study_subj_study_sequence_uq",
            ),
        ]
        verbose_name = "subject"
        verbose_name_plural = "subjects"


class SubjectEnrollment(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    status = models.CharField(max_length=32)
    status_datetime = models.DateTimeField(null=True, blank=True)
    status_reason_code = models.CharField(max_length=64, null=True, blank=True)
    status_reason_text = models.TextField(null=True, blank=True)

    is_enrolled = models.BooleanField(default=False)
    enrollment_date = models.DateField(null=True, blank=True)
    enrolled_by_id = models.BigIntegerField(null=True, blank=True)
    screen_failed_at = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)

    subject = models.OneToOneField(
        Subject,
        on_delete=models.DO_NOTHING,
        db_column="subject_id",
        related_name="enrollment",
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.DO_NOTHING,
        db_column="site_id",
        related_name="subject_enrollments",
    )
    study = models.ForeignKey(
        Study,
        on_delete=models.DO_NOTHING,
        db_column="study_id",
        related_name="subject_enrollments",
    )
    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "study_subject_enrollment"
        managed = False
        default_permissions = ()
        indexes = [
            models.Index(
                fields=["study", "site", "status"],
                name="study_suben_std_site_st_ix",
            ),
            models.Index(
                fields=["study", "is_enrolled"],
                name="study_suben_study_enr_ix",
            ),
        ]
        verbose_name = "subject enrollment"
        verbose_name_plural = "subject enrollments"


class SubjectRandomization(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    randomization_status = models.CharField(max_length=16, null=True, blank=True)
    randomization_datetime = models.DateTimeField(null=True, blank=True)
    randomization_sequence = models.CharField(max_length=64, null=True, blank=True)
    randomization_number = models.CharField(max_length=64, null=True, blank=True)
    randomization_source = models.CharField(max_length=16, null=True, blank=True)
    randomized_by_id = models.BigIntegerField(null=True, blank=True)

    subject = models.OneToOneField(
        Subject,
        on_delete=models.DO_NOTHING,
        db_column="subject_id",
        related_name="randomization",
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.DO_NOTHING,
        db_column="site_id",
        related_name="subject_randomizations",
    )
    study = models.ForeignKey(
        Study,
        on_delete=models.DO_NOTHING,
        db_column="study_id",
        related_name="subject_randomizations",
    )
    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "study_subject_randomization"
        managed = False
        default_permissions = ()
        indexes = [
            models.Index(
                fields=["study", "site", "randomization_status"],
                name="study_srand_std_site_st_ix",
            ),
            models.Index(
                fields=["study", "randomization_number"],
                name="study_srand_st_num_ix",
            ),
        ]
        verbose_name = "subject randomization"
        verbose_name_plural = "subject randomizations"


class SubjectEventInstance(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    study = models.ForeignKey(
        Study,
        on_delete=models.DO_NOTHING,
        db_column="study_id",
        related_name="subject_event_instances",
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.DO_NOTHING,
        db_column="subject_id",
        related_name="event_instances",
    )
    event_definition = models.ForeignKey(
        EventDefinition,
        on_delete=models.DO_NOTHING,
        db_column="event_definition_id",
        related_name="subject_event_instances",
    )
    study_version = models.CharField(max_length=20)

    repeat_index = models.IntegerField(default=1)

    planned_date = models.DateTimeField(null=True, blank=True)
    target_date = models.DateTimeField(null=True, blank=True)
    actual_date = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=32, default="not_ready")

    opened_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)

    opened_by_id = models.BigIntegerField(null=True, blank=True)
    completed_by_id = models.BigIntegerField(null=True, blank=True)
    verified_by_id = models.BigIntegerField(null=True, blank=True)
    locked_by_id = models.BigIntegerField(null=True, blank=True)

    skip_reason = models.TextField(null=True, blank=True)
    cancel_reason = models.TextField(null=True, blank=True)

    event_code_snapshot = models.CharField(max_length=64, null=True, blank=True)
    event_name_snapshot = models.CharField(max_length=255, null=True, blank=True)
    event_type_snapshot = models.CharField(max_length=32, null=True, blank=True)

    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "study_eventinstance"
        managed = False
        default_permissions = ()
        indexes = [
            models.Index(
                fields=["study", "subject"],
                name="sub_evtins_st_sub_idx",
            ),
            models.Index(
                fields=["subject", "status"],
                name="sub_evtins_sub_st_idx",
            ),
            models.Index(
                fields=["planned_date"],
                name="sub_evtins_plan_dt_idx",
            ),
            models.Index(
                fields=["actual_date"],
                name="sub_evtins_act_dt_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["subject", "event_definition", "repeat_index"],
                name="study_eventinstance_subject_event_repeat_uniq",
            )
        ]
        verbose_name = "subject event instance"
        verbose_name_plural = "subject event instances"
