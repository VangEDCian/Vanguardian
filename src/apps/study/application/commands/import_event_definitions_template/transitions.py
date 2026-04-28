from apps.study.application.commands.import_event_definitions_template.types import EventDefinitionImportFormatError


class EventDefinitionTransitionMixin:
    def _sync_transition_rule(
        self,
        *,
        event_definition,
        study_id,
        study_version,
        sequence_no,
        precondition_code,
        transition_type,
        condition_scope,
        condition_code,
        condition_expression,
        offset_days,
        window_before_days,
        window_after_days,
        auto_open,
        auto_create,
        requires_previous_completion,
        allow_skip,
        actor_user_id,
        now,
    ):
        if not precondition_code:
            self.repository.soft_delete_transition_rules_for_event(
                study_id=study_id,
                study_version=study_version,
                to_event_definition=event_definition,
                actor_user_id=actor_user_id,
                updated_at=now,
            )
            return

        from_event_definition = self.repository.get_active_event_definition_by_code(
            study_id=study_id,
            study_version=study_version,
            code=precondition_code,
        )
        if from_event_definition is None:
            raise EventDefinitionImportFormatError(
                f"Precondition event {precondition_code!r} was not found in study version {study_version!r}."
            )

        self.repository.soft_delete_transition_rules_for_event(
            study_id=study_id,
            study_version=study_version,
            to_event_definition=event_definition,
            exclude_from_event_definition=from_event_definition,
            actor_user_id=actor_user_id,
            updated_at=now,
        )

        transition_defaults = {
            "transition_type": transition_type,
            "condition_scope": condition_scope,
            "condition_code": condition_code,
            "condition_expression": condition_expression,
            "offset_days": offset_days,
            "window_before_days": window_before_days,
            "window_after_days": window_after_days,
            "auto_open": auto_open,
            "auto_create": auto_create,
            "requires_previous_completion": requires_previous_completion,
            "allow_skip": allow_skip,
            "display_order": sequence_no,
            "is_enabled": True,
            "deleted": False,
            "updated_at": now,
            "updated_by_id": actor_user_id,
        }

        transition_rule = self.repository.get_transition_rule(
            study_id=study_id,
            study_version=study_version,
            to_event_definition=event_definition,
            from_event_definition=from_event_definition,
        )

        if transition_rule is None:
            self.repository.create_transition_rule(
                study_id=study_id,
                study_version=study_version,
                from_event_definition=from_event_definition,
                to_event_definition=event_definition,
                created_at=now,
                created_by_id=actor_user_id,
                **transition_defaults,
            )
            return

        for field_name, value in transition_defaults.items():
            setattr(transition_rule, field_name, value)
        self.repository.save_transition_rule(transition_rule, update_fields=list(transition_defaults.keys()))
