from django.db import models

from apps.core.choices.study import RandomizationSchemeStatusChoice, RandomizationSlotStatusChoice


class RandomizationScheme(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    study = models.ForeignKey(
        "study.Study",
        on_delete=models.DO_NOTHING,
        db_column="study_id",
        related_name="randomization_schemes",
    )

    code = models.CharField(max_length=64)
    name = models.CharField(max_length=255)

    randomization_type = models.CharField(max_length=32)
    allocation_ratio_json = models.JSONField(null=True, blank=True)

    target_randomized_total = models.PositiveIntegerField()
    eligibility_rule_code = models.CharField(max_length=64, null=True, blank=True)
    requires_screening_pass = models.BooleanField(default=True)
    is_open_label = models.BooleanField(default=True)

    status = models.CharField(
        max_length=32,
        choices=RandomizationSchemeStatusChoice,
        default=RandomizationSchemeStatusChoice.DRAFT,
    )
    effective_from = models.DateTimeField(null=True, blank=True)
    effective_to = models.DateTimeField(null=True, blank=True)

    created_by_id = models.BigIntegerField(null=True, blank=True)
    approved_by_id = models.BigIntegerField(null=True, blank=True)

    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "study_randomization_scheme"
        managed = True
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["study", "code"],
                name="study_randsch_study_code_uq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["study", "code"],
                name="study_randsch_code_idx",
            ),
            models.Index(
                fields=["study", "status"],
                name="study_randsch_study_status_ix",
            ),
        ]
        verbose_name = "study randomization scheme"
        verbose_name_plural = "study randomization schemes"


class RandomizationArm(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    scheme = models.ForeignKey(
        RandomizationScheme,
        on_delete=models.DO_NOTHING,
        db_column="scheme_id",
        related_name="arms",
    )

    arm_code = models.CharField(max_length=32)
    arm_name = models.CharField(max_length=255)

    target_count = models.IntegerField()
    current_count = models.IntegerField(default=0)

    display_order = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)

    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "study_randomization_arm"
        managed = True
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["scheme", "arm_code"],
                name="study_randarm_scheme_code_uq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["scheme", "arm_code"],
                name="study_randarm_code_idx",
            ),
            models.Index(
                fields=["scheme", "display_order"],
                name="study_randarm_scheme_order_ix",
            ),
        ]
        verbose_name = "study randomization arm"
        verbose_name_plural = "study randomization arms"


class RandomizationSlot(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    scheme = models.ForeignKey(
        RandomizationScheme,
        on_delete=models.DO_NOTHING,
        db_column="scheme_id",
        related_name="slots",
    )
    arm = models.ForeignKey(
        RandomizationArm,
        on_delete=models.DO_NOTHING,
        db_column="arm_id",
        related_name="slots",
    )

    sequence_no = models.IntegerField()
    block_no = models.IntegerField(null=True, blank=True)
    stratum_code = models.CharField(max_length=64, null=True, blank=True)

    status = models.CharField(
        max_length=32,
        choices=RandomizationSlotStatusChoice,
        default="available",
    )
    assigned_subject_id = models.BigIntegerField(null=True, blank=True)
    assigned_event_id = models.BigIntegerField(null=True, blank=True)
    assigned_at = models.DateTimeField(null=True, blank=True)

    void_reason = models.CharField(max_length=255, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "study_randomization_slot"
        managed = True
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["scheme", "sequence_no"],
                name="study_rslot_scheme_seq_uq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["scheme", "sequence_no"],
                name="study_rslot_seq_idx",
            ),
            models.Index(
                fields=["scheme", "status"],
                name="study_rslot_scheme_status_ix",
            ),
            models.Index(
                fields=["arm", "status"],
                name="study_rslot_arm_status_ix",
            ),
            models.Index(
                fields=["assigned_subject_id"],
                name="study_rslot_subject_ix",
            ),
        ]
        verbose_name = "study randomization slot"
        verbose_name_plural = "study randomization slots"

