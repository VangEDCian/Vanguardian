from django.db import models

from apps.core.choices import (
    EligibilityAssessmentStatusChoices,
    EligibilityAssessmentTypeChoices,
    EligibilityCriterionTypeChoices,
    EligibilityResultChoices,
)

from .site import Site
from .study import Study


class SubjectEligibilityAssessment(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    study = models.ForeignKey(
        Study,
        on_delete=models.DO_NOTHING,
        db_column="study_id",
        related_name="subject_eligibility_assessments",
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.DO_NOTHING,
        db_column="site_id",
        related_name="subject_eligibility_assessments",
    )
    subject_id = models.BigIntegerField()
    event_instance_id = models.BigIntegerField(null=True, blank=True)

    assessment_type = models.CharField(
        max_length=32,
        choices=EligibilityAssessmentTypeChoices.choices,
    )
    assessment_no = models.IntegerField(default=1)
    result = models.CharField(
        max_length=32,
        choices=EligibilityResultChoices.choices,
    )
    assessment_status = models.CharField(
        max_length=32,
        choices=EligibilityAssessmentStatusChoices.choices,
    )
    is_current = models.BooleanField(default=True)

    assessed_by_id = models.BigIntegerField(null=True, blank=True)
    assessed_at = models.DateTimeField(null=True, blank=True)
    finalized_by_id = models.BigIntegerField(null=True, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    retracted_by_id = models.BigIntegerField(null=True, blank=True)
    retracted_at = models.DateTimeField(null=True, blank=True)
    protocol_version = models.CharField(max_length=32, null=True, blank=True)
    study_version = models.CharField(max_length=20)
    crf_version = models.CharField(max_length=32, null=True, blank=True)

    source_context = models.CharField(max_length=64, default="datacapture")
    source_object_type = models.CharField(max_length=64, null=True, blank=True)
    source_object_id = models.BigIntegerField(null=True, blank=True)
    source_page_state_id = models.BigIntegerField(null=True, blank=True)
    source_page_entry_id = models.BigIntegerField(null=True, blank=True)
    source_data_version = models.IntegerField(null=True, blank=True)
    source_data_hash = models.CharField(max_length=64, null=True, blank=True)

    rule_code = models.CharField(max_length=64, null=True, blank=True)
    rule_version = models.CharField(max_length=20, null=True, blank=True)
    conclusion_field_key = models.CharField(max_length=128, null=True, blank=True)
    conclusion_value = models.CharField(max_length=64, null=True, blank=True)
    facts_json = models.TextField(null=True, blank=True)
    failed_conditions_json = models.TextField(null=True, blank=True)
    failure_reason_code = models.CharField(max_length=64, null=True, blank=True)
    failure_reason_text = models.TextField(null=True, blank=True)
    reason_code = models.CharField(max_length=64, null=True, blank=True)
    reason_text = models.TextField(null=True, blank=True)

    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "study_subject_eligibility_assessment"
        managed = True
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["subject_id", "assessment_type", "assessment_no"],
                name="st_subj_elig_assess_uq",
            )
        ]
        indexes = [
            models.Index(
                fields=["study", "site", "result", "assessment_status"],
                name="st_subj_elig_result_idx",
            ),
            models.Index(
                fields=["subject_id", "assessment_status", "is_current"],
                name="st_subj_elig_status_idx",
            ),
            models.Index(
                fields=["study", "study_version", "rule_code"],
                name="study_subj_elig_rule_idx",
            ),
            models.Index(
                fields=["source_context", "source_object_type", "source_object_id"],
                name="study_subj_elig_source_idx",
            ),
            models.Index(
                fields=["event_instance_id", "assessment_status"],
                name="st_subj_elig_event_idx",
            ),
        ]
        verbose_name = "subject eligibility assessment"
        verbose_name_plural = "subject eligibility assessments"


class SubjectEligibilityFailure(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    assessment = models.ForeignKey(
        SubjectEligibilityAssessment,
        on_delete=models.DO_NOTHING,
        db_column="assessment_id",
        related_name="failures",
    )
    criterion_code = models.CharField(max_length=128, null=True, blank=True)
    criterion_type = models.CharField(
        max_length=32,
        choices=EligibilityCriterionTypeChoices.choices,
    )
    criterion_label_snapshot = models.TextField(null=True, blank=True)
    expected_value = models.TextField(null=True, blank=True)
    actual_value = models.TextField(null=True, blank=True)
    value_type = models.CharField(max_length=32, null=True, blank=True)
    source_context = models.CharField(max_length=64, null=True, blank=True)
    source_object_type = models.CharField(max_length=64, null=True, blank=True)
    source_object_id = models.BigIntegerField(null=True, blank=True)
    source_field_key = models.CharField(max_length=128, null=True, blank=True)
    source_field_template_id = models.BigIntegerField(null=True, blank=True)
    reason_code = models.CharField(max_length=64, null=True, blank=True)
    reason_text = models.TextField(null=True, blank=True)
    display_order = models.IntegerField(default=1)
    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "study_subject_eligibility_failure"
        managed = True
        default_permissions = ()
        indexes = [
            models.Index(
                fields=["assessment", "display_order"],
                name="study_subj_elig_fail_order_idx",
            ),
            models.Index(
                fields=["assessment", "criterion_type"],
                name="study_subj_elig_fail_type_idx",
            ),
            models.Index(
                fields=["source_field_key"],
                name="study_subj_elig_fail_field_idx",
            ),
        ]
        verbose_name = "subject eligibility failure"
        verbose_name_plural = "subject eligibility failures"


__all__ = ["SubjectEligibilityAssessment", "SubjectEligibilityFailure"]
