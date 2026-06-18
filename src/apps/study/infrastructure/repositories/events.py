from apps.study.infrastructure.persistence.models import (
    ConditionDefinition,
    EventDefinition,
    EventFormBinding,
    EventTransitionRule,
)


class DjangoStudyEventRepository:
    def find_study_version(self, *, study_id, study_version):
        return (
            EventDefinition.objects.filter(
                study_id=study_id,
                study_version__iexact=study_version,
            )
            .values_list("study_version", flat=True)
            .first()
        )

    def get_event_definition_for_import(self, *, study_id, study_version, code):
        return EventDefinition.objects.filter(
            study_id=study_id,
            study_version=study_version,
            code=code,
        ).first()

    def create_event_definition(self, **values):
        return EventDefinition.objects.create(**values)

    def save_event_definition(self, event_definition, *, update_fields):
        event_definition.save(update_fields=update_fields)
        return event_definition

    def get_condition_definition(self, *, study_id, study_version, code):
        return ConditionDefinition.objects.filter(
            study_id=study_id,
            study_version=study_version,
            code=code,
        ).first()

    def create_condition_definition(self, **values):
        return ConditionDefinition.objects.create(**values)

    def save_condition_definition(self, condition_definition, *, update_fields):
        condition_definition.save(update_fields=update_fields)
        return condition_definition

    def get_active_event_definition_by_code(self, *, study_id, study_version, code):
        return EventDefinition.objects.filter(
            study_id=study_id,
            study_version=study_version,
            code__iexact=code,
            deleted=False,
        ).first()

    def list_active_event_definitions_by_code(self, *, study_id, code):
        return EventDefinition.objects.filter(
            study_id=study_id,
            deleted=False,
            code__iexact=code,
        ).order_by("pk")

    def soft_delete_transition_rules_for_event(
        self,
        *,
        study_id,
        study_version,
        to_event_definition,
        actor_user_id,
        updated_at,
        exclude_from_event_definition=None,
    ):
        queryset = EventTransitionRule.objects.filter(
            study_id=study_id,
            study_version=study_version,
            to_event_definition=to_event_definition,
            deleted=False,
        )
        if exclude_from_event_definition is not None:
            queryset = queryset.exclude(from_event_definition=exclude_from_event_definition)
        return queryset.update(
            deleted=True,
            updated_at=updated_at,
            updated_by_id=actor_user_id,
        )

    def get_transition_rule(self, *, study_id, study_version, to_event_definition, from_event_definition):
        return EventTransitionRule.objects.filter(
            study_id=study_id,
            study_version=study_version,
            to_event_definition=to_event_definition,
            from_event_definition=from_event_definition,
        ).first()

    def create_transition_rule(self, **values):
        return EventTransitionRule.objects.create(**values)

    def save_transition_rule(self, transition_rule, *, update_fields):
        transition_rule.save(update_fields=update_fields)
        return transition_rule

    def get_event_form_binding(self, *, event_definition_id, form_definition_id):
        return EventFormBinding.objects.filter(
            event_definition_id=event_definition_id,
            form_definition_id=form_definition_id,
        ).first()

    def soft_delete_event_form_bindings_for_import(self, *, event_definition_ids, actor_user_id, updated_at):
        normalized_ids = tuple(int(event_definition_id) for event_definition_id in event_definition_ids or ())
        if not normalized_ids:
            return 0
        return EventFormBinding.objects.filter(
            event_definition_id__in=normalized_ids,
            deleted=False,
        ).update(
            deleted=True,
            updated_at=updated_at,
            updated_by_id=actor_user_id,
        )

    def create_event_form_binding(self, **values):
        return EventFormBinding.objects.create(**values)

    def save_event_form_binding(self, binding, *, update_fields):
        binding.save(update_fields=update_fields)
        return binding
