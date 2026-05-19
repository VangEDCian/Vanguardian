from django.db import models

from apps.core.choices import (
    EventDefinitionCategoryChoices,
    EventDefinitionTimingModeChoices,
    EventDefinitionTypeChoices,
    EventExecutionModeChoices,
    EventTransitionConditionScopeChoices,
    EventTransitionTypeChoices,
    StudyConditionDefinitionScopeChoices,
    StudyConditionDefinitionStatusChoices,
)
from apps.shared.constants import EventFormEntryModeChoices

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
    study_version = models.CharField(max_length=20)

    code = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    event_type = models.CharField(
        max_length=32,
        choices=EventDefinitionTypeChoices.choices,
    )
    timing_mode = models.CharField(
        max_length=32,
        choices=EventDefinitionTimingModeChoices.choices,
        default=EventDefinitionTimingModeChoices.SCHEDULED,
    )
    event_category = models.CharField(
        max_length=32,
        choices=EventDefinitionCategoryChoices.choices,
        null=True,
        blank=True,
    )
    execution_mode = models.CharField(
        max_length=32,
        choices=EventExecutionModeChoices.choices,
        default=EventExecutionModeChoices.FORM_ENTRY,
    )

    sequence_no = models.IntegerField(default=1)
    phase_code = models.CharField(max_length=64, null=True, blank=True)

    is_repeating = models.BooleanField(default=False)
    max_repeats = models.IntegerField(null=True, blank=True)

    is_enabled = models.BooleanField(default=True)
    is_required = models.BooleanField(default=False)

    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "study_eventdefinition"
        managed = True
        default_permissions = ()
        permissions = (
            ("view_study_eventdefinition_list", "Can view study event definition list"),
            ("create_study_eventdefinition", "Can create study event definition"),
            ("update_study_eventdefinition", "Can update study event definition"),
            ("delete_study_eventdefinition", "Can delete study event definition"),
        )
        constraints = [
            models.UniqueConstraint(
                fields=["study", "study_version", "code"],
                name="study_eventdefinition_study_version_code_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=["study", "study_version", "code"],
                name="std_evtdef_ver_code_idx",
            ),
            models.Index(
                fields=["study", "study_version", "sequence_no"],
                name="std_evtdef_ver_seq_idx",
            )
        ]
        verbose_name = "study event definition"
        verbose_name_plural = "study event definitions"


class ConditionDefinition(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    study = models.ForeignKey(
        Study,
        on_delete=models.DO_NOTHING,
        db_column="study_id",
        related_name="condition_definitions",
    )
    study_version = models.CharField(max_length=20)

    code = models.CharField(max_length=64)
    scope = models.CharField(
        max_length=32,
        choices=StudyConditionDefinitionScopeChoices.choices,
    )
    expression_json = models.TextField()

    status = models.CharField(
        max_length=32,
        choices=StudyConditionDefinitionStatusChoices.choices,
        default=StudyConditionDefinitionStatusChoices.DRAFT,
    )
    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)
    approved_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "study_condition_definition"
        managed = True
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["study", "study_version", "code"],
                name="std_conddef_code_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=["study", "study_version", "status"],
                name="std_conddef_status_idx",
            ),
        ]
        verbose_name = "study condition definition"
        verbose_name_plural = "study condition definitions"


class EventTransitionRule(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    study = models.ForeignKey(
        Study,
        on_delete=models.DO_NOTHING,
        db_column="study_id",
        related_name="event_transition_rules",
    )
    study_version = models.CharField(max_length=20)

    from_event_definition = models.ForeignKey(
        EventDefinition,
        on_delete=models.DO_NOTHING,
        db_column="from_event_definition_id",
        related_name="outgoing_transition_rules",
    )
    to_event_definition = models.ForeignKey(
        EventDefinition,
        on_delete=models.DO_NOTHING,
        db_column="to_event_definition_id",
        related_name="incoming_transition_rules",
    )

    transition_type = models.CharField(
        max_length=32,
        choices=EventTransitionTypeChoices.choices,
        default=EventTransitionTypeChoices.SEQUENTIAL,
    )
    condition_scope = models.CharField(
        max_length=32,
        choices=EventTransitionConditionScopeChoices.choices,
        default=EventTransitionConditionScopeChoices.SUBJECT_EVENT,
    )
    condition_code = models.CharField(max_length=64, null=True, blank=True)
    condition_definition = models.ForeignKey(
        ConditionDefinition,
        on_delete=models.DO_NOTHING,
        db_column="condition_definition_id",
        related_name="event_transition_rules",
        null=True,
        blank=True,
    )

    offset_days = models.IntegerField(null=True, blank=True)
    window_before_days = models.IntegerField(null=True, blank=True)
    window_after_days = models.IntegerField(null=True, blank=True)

    auto_open = models.BooleanField(default=False)
    auto_create = models.BooleanField(default=False)
    requires_previous_completion = models.BooleanField(default=True)
    allow_skip = models.BooleanField(default=False)

    display_order = models.IntegerField(default=1)
    is_enabled = models.BooleanField(default=True)

    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "study_event_transition_rule"
        managed = True
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["study", "study_version", "from_event_definition", "to_event_definition"],
                name="study_eventtransition_from_to_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=["study", "study_version", "from_event_definition", "to_event_definition"],
                name="std_evttr_from_to_idx",
            ),
            models.Index(
                fields=["study", "study_version", "display_order"],
                name="std_evttr_disp_idx",
            ),
            models.Index(
                fields=["to_event_definition", "is_enabled"],
                name="std_evttr_to_en_idx",
            ),
            models.Index(
                fields=["condition_definition", "is_enabled"],
                name="std_evttr_cond_en_idx",
            ),
        ]
        verbose_name = "study event transition rule"
        verbose_name_plural = "study event transition rules"


class EventFormBinding(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    study = models.ForeignKey(
        Study,
        on_delete=models.DO_NOTHING,
        db_column="study_id",
        related_name="event_form_bindings",
    )
    study_version = models.CharField(max_length=20)

    event_definition = models.ForeignKey(
        EventDefinition,
        on_delete=models.DO_NOTHING,
        db_column="event_definition_id",
        related_name="form_bindings",
    )
    form_definition = models.ForeignKey(
        "crf.CrfTemplate",
        on_delete=models.DO_NOTHING,
        db_column="form_definition_id",
        related_name="event_form_bindings",
    )

    display_order = models.IntegerField(default=1)

    is_required = models.BooleanField(default=True)
    is_enabled = models.BooleanField(default=True)
    is_repeatable_within_event = models.BooleanField(default=False)

    role_scope = models.CharField(max_length=64, null=True, blank=True)
    entry_mode = models.CharField(
        max_length=32,
        choices=EventFormEntryModeChoices.choices,
        null=True,
        blank=True,
    )

    created_by_id = models.BigIntegerField(null=True, blank=True)
    updated_by_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "study_eventformbinding"
        managed = True
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["event_definition", "form_definition"],
                name="study_eventformbinding_event_form_uniq",
            )
        ]
        indexes = [
            models.Index(
                fields=["event_definition", "form_definition"],
                name="std_evtbind_evt_form_idx",
            ),
            models.Index(
                fields=["event_definition", "display_order"],
                name="study_evtbind_evt_order_idx",
            )
        ]
        verbose_name = "study event form binding"
        verbose_name_plural = "study event form bindings"
