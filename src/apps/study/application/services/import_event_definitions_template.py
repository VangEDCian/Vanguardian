from django.db import transaction

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
from apps.study.application.commands.import_event_definitions_template.transitions import EventDefinitionTransitionMixin
from apps.study.application.commands.import_event_definitions_template.types import (
    EventDefinitionImportFormatError,
    EventDefinitionImportIssue,
    ImportStudyEventDefinitionsTemplateCommand,
    ImportStudyEventDefinitionsTemplateResult,
)
from apps.study.application.commands.import_event_definitions_template.workbook import EventDefinitionWorkbookMixin
from apps.study.infrastructure.repositories import DjangoStudyEventRepository


class ImportStudyEventDefinitionsTemplateService(EventDefinitionTransitionMixin, EventDefinitionWorkbookMixin):
    repository_class = DjangoStudyEventRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    expected_columns = (
        "Study Version",
        "Code",
        "Name",
        "Description",
        "Event Type",
        "Timing Mode",
        "Event Category",
        "Execution Mode",
        "Sequence No",
        "Phase Code",
        "Repeated",
        "Max Repeats",
        "Required",
        "Precondition",
        "Transition Type",
        "Condition Scope",
        "Condition Code",
        "Condition Expression",
        "Offset Days",
        "Window Before Days",
        "Window After Days",
        "Auto Open",
        "Auto Create",
        "Requires Previous Completion",
        "Allow Skip",
    )
    expected_header_map = {
        "study code": "study_code",
        "study version": "study_version",
        "code": "code",
        "name": "name",
        "description": "description",
        "event type": "event_type",
        "timing mode": "timing_mode",
        "event category": "event_category",
        "execution mode": "execution_mode",
        "sequence no": "sequence_no",
        "phase code": "phase_code",
        "repeated": "repeated",
        "max repeats": "max_repeats",
        "required": "required",
        "precondition": "precondition",
        "transition type": "transition_type",
        "condition scope": "condition_scope",
        "condition code": "condition_code",
        "condition expression": "condition_expression",
        "offset days": "offset_days",
        "window before days": "window_before_days",
        "window after days": "window_after_days",
        "auto open": "auto_open",
        "auto create": "auto_create",
        "requires previous completion": "requires_previous_completion",
        "allow skip": "allow_skip",
    }
    event_type_aliases = {
        "visit_based": EventDefinitionTypeChoices.VISIT_BASED,
        "visit based": EventDefinitionTypeChoices.VISIT_BASED,
        "visit-based": EventDefinitionTypeChoices.VISIT_BASED,
        "common": EventDefinitionTypeChoices.COMMON,
        "operational": EventDefinitionTypeChoices.OPERATIONAL,
    }
    timing_mode_aliases = {
        "scheduled": EventDefinitionTimingModeChoices.SCHEDULED,
        "unscheduled": EventDefinitionTimingModeChoices.UNSCHEDULED,
        "conditional": EventDefinitionTimingModeChoices.CONDITIONAL,
    }
    event_category_aliases = {
        "screening": EventDefinitionCategoryChoices.SCREENING,
        "randomization": EventDefinitionCategoryChoices.RANDOMIZATION,
        "treatment": EventDefinitionCategoryChoices.TREATMENT,
        "washout": EventDefinitionCategoryChoices.WASHOUT,
        "follow_up": EventDefinitionCategoryChoices.FOLLOW_UP,
        "follow up": EventDefinitionCategoryChoices.FOLLOW_UP,
        "follow-up": EventDefinitionCategoryChoices.FOLLOW_UP,
        "eos": EventDefinitionCategoryChoices.EOS,
        "end of study": EventDefinitionCategoryChoices.EOS,
        "unscheduled": EventDefinitionCategoryChoices.UNSCHEDULED,
    }
    execution_mode_aliases = {
        "form_entry": EventExecutionModeChoices.FORM_ENTRY,
        "form entry": EventExecutionModeChoices.FORM_ENTRY,
        "form-entry": EventExecutionModeChoices.FORM_ENTRY,
        "workflow_action": EventExecutionModeChoices.WORKFLOW_ACTION,
        "workflow action": EventExecutionModeChoices.WORKFLOW_ACTION,
        "workflow-action": EventExecutionModeChoices.WORKFLOW_ACTION,
        "hybrid": EventExecutionModeChoices.HYBRID,
    }
    transition_type_aliases = {
        "sequential": EventTransitionTypeChoices.SEQUENTIAL,
        "conditional": EventTransitionTypeChoices.CONDITIONAL,
    }
    transition_condition_scope_aliases = {
        "subject": EventTransitionConditionScopeChoices.SUBJECT,
        "subject_event": EventTransitionConditionScopeChoices.SUBJECT_EVENT,
        "subject event": EventTransitionConditionScopeChoices.SUBJECT_EVENT,
        "subject-event": EventTransitionConditionScopeChoices.SUBJECT_EVENT,
        "subject_period": EventTransitionConditionScopeChoices.SUBJECT_PERIOD,
        "subject period": EventTransitionConditionScopeChoices.SUBJECT_PERIOD,
        "subject-period": EventTransitionConditionScopeChoices.SUBJECT_PERIOD,
        "randomization": EventTransitionConditionScopeChoices.RANDOMIZATION,
        "eligibility": EventTransitionConditionScopeChoices.ELIGIBILITY,
    }
    condition_definition_scope_aliases = {
        "subject": StudyConditionDefinitionScopeChoices.SUBJECT,
        "subject_event": StudyConditionDefinitionScopeChoices.EVENT,
        "subject event": StudyConditionDefinitionScopeChoices.EVENT,
        "subject-event": StudyConditionDefinitionScopeChoices.EVENT,
        "event": StudyConditionDefinitionScopeChoices.EVENT,
        "subject_period": StudyConditionDefinitionScopeChoices.PERIOD,
        "subject period": StudyConditionDefinitionScopeChoices.PERIOD,
        "subject-period": StudyConditionDefinitionScopeChoices.PERIOD,
        "period": StudyConditionDefinitionScopeChoices.PERIOD,
        "randomization": StudyConditionDefinitionScopeChoices.RANDOMIZATION,
        "eligibility": StudyConditionDefinitionScopeChoices.ELIGIBILITY,
        "page": StudyConditionDefinitionScopeChoices.PAGE,
    }
    true_values = {"true", "1", "yes", "y"}
    false_values = {"", "false", "0", "no", "n"}

    def execute(self, command: ImportStudyEventDefinitionsTemplateCommand) -> ImportStudyEventDefinitionsTemplateResult:
        workbook_rows = self._load_rows_from_workbook(
            file_name=command.file_name,
            file_content=command.file_content,
        )

        created_count = 0
        updated_count = 0
        issues = []

        for row_number, row_data in workbook_rows:
            try:
                import_outcome = self._import_row(
                    study_id=command.study_id,
                    row_data=row_data,
                    row_number=row_number,
                    actor_user_id=command.actor_user_id,
                )
            except EventDefinitionImportFormatError as exc:
                issues.append(
                    EventDefinitionImportIssue(
                        row_number=row_number,
                        study_code=str(row_data.get("study_code", "") or ""),
                        code=str(row_data.get("code", "") or ""),
                        reason=str(exc),
                    )
                )
                continue

            if import_outcome == "created":
                created_count += 1
            else:
                updated_count += 1

        return ImportStudyEventDefinitionsTemplateResult(
            total_rows=len(workbook_rows),
            created_count=created_count,
            updated_count=updated_count,
            skipped_count=len(issues),
            issues=tuple(issues),
            warnings=(),
        )

    def _import_row(self, *, study_id, row_data, row_number, actor_user_id):
        study_version_input = self._as_text(row_data.get("study_version"))
        if not study_version_input:
            raise EventDefinitionImportFormatError("Study Version is required.")
        if len(study_version_input) > 20:
            raise EventDefinitionImportFormatError("Study Version must be 20 characters or fewer.")

        study_version = self._resolve_study_version(
            study_id=study_id,
            raw_study_version=study_version_input,
        )

        code = self._as_text(row_data.get("code"))
        if not code:
            raise EventDefinitionImportFormatError("Code is required.")

        name = self._as_text(row_data.get("name"))
        if not name:
            raise EventDefinitionImportFormatError("Name is required.")

        event_type = self._normalize_choice(
            raw_value=row_data.get("event_type"),
            aliases=self.event_type_aliases,
            field_label="Event Type",
        )
        timing_mode = self._normalize_choice(
            raw_value=row_data.get("timing_mode"),
            aliases=self.timing_mode_aliases,
            field_label="Timing Mode",
        )
        event_category = self._normalize_choice(
            raw_value=row_data.get("event_category"),
            aliases=self.event_category_aliases,
            field_label="Event Category",
            allow_blank=True,
        )
        execution_mode = self._normalize_choice(
            raw_value=row_data.get("execution_mode"),
            aliases=self.execution_mode_aliases,
            field_label="Execution Mode",
            allow_blank=True,
        ) or EventExecutionModeChoices.FORM_ENTRY
        precondition_code = self._nullable_text(row_data.get("precondition"))

        sequence_no = self._coerce_int(row_data.get("sequence_no"), field_label="Sequence No", default=1)
        max_repeats = self._coerce_int(row_data.get("max_repeats"), field_label="Max Repeats", allow_blank=True)

        if precondition_code:
            transition_type = self._normalize_choice(
                raw_value=row_data.get("transition_type"),
                aliases=self.transition_type_aliases,
                field_label="Transition Type",
                allow_blank=True,
            ) or EventTransitionTypeChoices.SEQUENTIAL
            condition_scope = self._normalize_choice(
                raw_value=row_data.get("condition_scope"),
                aliases=self.transition_condition_scope_aliases,
                field_label="Condition Scope",
                allow_blank=True,
            ) or EventTransitionConditionScopeChoices.SUBJECT_EVENT
            condition_code = self._nullable_text(row_data.get("condition_code"))
            condition_expression = self._nullable_text(row_data.get("condition_expression"))
            condition_definition_scope = self._condition_definition_scope_from_transition_scope(condition_scope)
            if condition_expression and not condition_code:
                raise EventDefinitionImportFormatError(
                    "Condition Code is required when Condition Expression is provided."
                )
            offset_days = self._coerce_int(row_data.get("offset_days"), field_label="Offset Days", allow_blank=True)
            window_before_days = self._coerce_int(
                row_data.get("window_before_days"),
                field_label="Window Before Days",
                allow_blank=True,
            )
            window_after_days = self._coerce_int(
                row_data.get("window_after_days"),
                field_label="Window After Days",
                allow_blank=True,
            )
            auto_open = self._coerce_bool(row_data.get("auto_open"), allow_blank=True, default=False)
            auto_create = self._coerce_bool(row_data.get("auto_create"), allow_blank=True, default=False)
            requires_previous_completion = self._coerce_bool(
                row_data.get("requires_previous_completion"),
                allow_blank=True,
                default=True,
            )
            allow_skip = self._coerce_bool(row_data.get("allow_skip"), allow_blank=True, default=False)
        else:
            transition_type = None
            condition_scope = None
            condition_code = None
            condition_expression = None
            condition_definition_scope = None
            offset_days = None
            window_before_days = None
            window_after_days = None
            auto_open = False
            auto_create = False
            requires_previous_completion = True
            allow_skip = False

        now = self._now()
        defaults = {
            "study_id": study_id,
            "study_version": study_version,
            "name": name,
            "description": self._nullable_text(row_data.get("description")),
            "event_type": event_type,
            "timing_mode": timing_mode,
            "event_category": event_category,
            "execution_mode": execution_mode,
            "sequence_no": sequence_no,
            "phase_code": self._nullable_text(row_data.get("phase_code")),
            "is_repeating": self._coerce_bool(row_data.get("repeated")),
            "max_repeats": max_repeats,
            "is_enabled": True,
            "is_required": self._coerce_bool(row_data.get("required")),
            "deleted": False,
            "updated_at": now,
            "updated_by_id": actor_user_id,
        }

        with transaction.atomic():
            event_definition = self.repository.get_event_definition_for_import(
                study_id=study_id,
                study_version=study_version,
                code=code,
            )

            if event_definition is None:
                event_definition = self.repository.create_event_definition(
                    code=code,
                    created_at=now,
                    created_by_id=actor_user_id,
                    **defaults,
                )
                condition_definition = self._sync_condition_definition(
                    study_id=study_id,
                    study_version=study_version,
                    condition_code=condition_code,
                    condition_scope=condition_definition_scope,
                    condition_expression=condition_expression,
                    actor_user_id=actor_user_id,
                    now=now,
                )
                self._sync_transition_rule(
                    event_definition=event_definition,
                    study_id=study_id,
                    study_version=study_version,
                    sequence_no=sequence_no,
                    precondition_code=precondition_code,
                    transition_type=transition_type,
                    condition_scope=condition_scope,
                    condition_code=None if condition_definition is not None else condition_code,
                    condition_definition=condition_definition,
                    offset_days=offset_days,
                    window_before_days=window_before_days,
                    window_after_days=window_after_days,
                    auto_open=auto_open,
                    auto_create=auto_create,
                    requires_previous_completion=requires_previous_completion,
                    allow_skip=allow_skip,
                    actor_user_id=actor_user_id,
                    now=now,
                )
                return "created"

            for field_name, value in defaults.items():
                setattr(event_definition, field_name, value)
            self.repository.save_event_definition(event_definition, update_fields=list(defaults.keys()))
            condition_definition = self._sync_condition_definition(
                study_id=study_id,
                study_version=study_version,
                condition_code=condition_code,
                condition_scope=condition_definition_scope,
                condition_expression=condition_expression,
                actor_user_id=actor_user_id,
                now=now,
            )
            self._sync_transition_rule(
                event_definition=event_definition,
                study_id=study_id,
                study_version=study_version,
                sequence_no=sequence_no,
                precondition_code=precondition_code,
                transition_type=transition_type,
                condition_scope=condition_scope,
                condition_code=None if condition_definition is not None else condition_code,
                condition_definition=condition_definition,
                offset_days=offset_days,
                window_before_days=window_before_days,
                window_after_days=window_after_days,
                auto_open=auto_open,
                auto_create=auto_create,
                requires_previous_completion=requires_previous_completion,
                allow_skip=allow_skip,
                actor_user_id=actor_user_id,
                now=now,
            )
            return "updated"

    def _sync_condition_definition(
        self,
        *,
        study_id,
        study_version,
        condition_code,
        condition_scope,
        condition_expression,
        actor_user_id,
        now,
    ):
        if not condition_expression:
            return None

        defaults = {
            "scope": condition_scope,
            "expression_json": condition_expression,
            "status": StudyConditionDefinitionStatusChoices.ACTIVE,
            "deleted": False,
            "updated_at": now,
            "updated_by_id": actor_user_id,
        }
        condition_definition = self.repository.get_condition_definition(
            study_id=study_id,
            study_version=study_version,
            code=condition_code,
        )
        if condition_definition is None:
            return self.repository.create_condition_definition(
                study_id=study_id,
                study_version=study_version,
                code=condition_code,
                created_at=now,
                created_by_id=actor_user_id,
                **defaults,
            )

        for field_name, value in defaults.items():
            setattr(condition_definition, field_name, value)
        return self.repository.save_condition_definition(
            condition_definition,
            update_fields=list(defaults.keys()),
        )

    def _condition_definition_scope_from_transition_scope(self, condition_scope):
        return self._normalize_choice(
            raw_value=condition_scope,
            aliases=self.condition_definition_scope_aliases,
            field_label="Condition Scope",
        )
