import json

from django.core.management.base import BaseCommand
from django.utils import timezone

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
from apps.study.models import ConditionDefinition, EventDefinition, EventTransitionRule


class Command(BaseCommand):
    help = "Seed sample SCREENING -> ELIGIBILITY_ASSESSMENT -> ENROLLMENT workflow declarations."

    def add_arguments(self, parser):
        parser.add_argument("--study-id", required=True, type=int)
        parser.add_argument("--study-version", required=True)
        parser.add_argument("--actor-id", type=int, default=None)
        parser.add_argument("--include-randomization", action="store_true")
        parser.add_argument("--include-screen-failure-event", action="store_true")

    def handle(self, *args, **options):
        study_id = options["study_id"]
        study_version = options["study_version"]
        actor_id = options["actor_id"]
        include_randomization = options["include_randomization"]
        include_screen_failure = options["include_screen_failure_event"]
        now = timezone.now()

        events = {
            "SCREENING": self._upsert_event(
                study_id=study_id,
                study_version=study_version,
                code="SCREENING",
                name="Screening / Sàng lọc",
                event_type=EventDefinitionTypeChoices.VISIT_BASED,
                timing_mode=EventDefinitionTimingModeChoices.SCHEDULED,
                event_category=EventDefinitionCategoryChoices.SCREENING,
                execution_mode=EventExecutionModeChoices.HYBRID,
                sequence_no=10,
                is_required=True,
                actor_id=actor_id,
                now=now,
            ),
            "ELIGIBILITY_ASSESSMENT": self._upsert_event(
                study_id=study_id,
                study_version=study_version,
                code="ELIGIBILITY_ASSESSMENT",
                name="Eligibility Assessment / Đánh giá đủ điều kiện",
                event_type=EventDefinitionTypeChoices.OPERATIONAL,
                timing_mode=EventDefinitionTimingModeChoices.CONDITIONAL,
                event_category=EventDefinitionCategoryChoices.SCREENING,
                execution_mode=EventExecutionModeChoices.WORKFLOW_ACTION,
                sequence_no=20,
                is_required=True,
                actor_id=actor_id,
                now=now,
            ),
            "ENROLLMENT": self._upsert_event(
                study_id=study_id,
                study_version=study_version,
                code="ENROLLMENT",
                name="Enrollment / Ghi danh",
                event_type=EventDefinitionTypeChoices.OPERATIONAL,
                timing_mode=EventDefinitionTimingModeChoices.CONDITIONAL,
                event_category=EventDefinitionCategoryChoices.SCREENING,
                execution_mode=EventExecutionModeChoices.WORKFLOW_ACTION,
                sequence_no=30,
                is_required=True,
                actor_id=actor_id,
                now=now,
            ),
        }
        if include_screen_failure:
            events["SCREEN_FAILURE"] = self._upsert_event(
                study_id=study_id,
                study_version=study_version,
                code="SCREEN_FAILURE",
                name="Screen Failure / Không đạt sàng lọc",
                event_type=EventDefinitionTypeChoices.OPERATIONAL,
                timing_mode=EventDefinitionTimingModeChoices.CONDITIONAL,
                event_category=EventDefinitionCategoryChoices.SCREENING,
                execution_mode=EventExecutionModeChoices.WORKFLOW_ACTION,
                sequence_no=25,
                is_required=False,
                actor_id=actor_id,
                now=now,
            )
        if include_randomization:
            events["RANDOMIZATION"] = self._upsert_event(
                study_id=study_id,
                study_version=study_version,
                code="RANDOMIZATION",
                name="Randomization / Phân ngẫu nhiên",
                event_type=EventDefinitionTypeChoices.OPERATIONAL,
                timing_mode=EventDefinitionTimingModeChoices.CONDITIONAL,
                event_category=EventDefinitionCategoryChoices.RANDOMIZATION,
                execution_mode=EventExecutionModeChoices.WORKFLOW_ACTION,
                sequence_no=40,
                is_required=False,
                actor_id=actor_id,
                now=now,
            )

        conditions = {
            "SCREENING_SOURCE_READY": self._upsert_condition(
                study_id=study_id,
                study_version=study_version,
                code="screening_source_ready",
                scope=StudyConditionDefinitionScopeChoices.EVENT,
                expression={
                    "any": [
                        {
                            "all": [
                                {"fact": "screening.page_state_is_verified", "operator": "equals", "value": True},
                                {"fact": "screening.non_bloking_queries", "operator": "equals", "value": True},
                            ]
                        },
                        {"fact": "screening.event_certified", "operator": "equals", "value": True},
                    ]
                },
                actor_id=actor_id,
                now=now,
            ),
            "ELIGIBILITY_FINAL_ELIGIBLE": self._upsert_condition(
                study_id=study_id,
                study_version=study_version,
                code="ELIGIBILITY_FINAL_ELIGIBLE",
                scope=StudyConditionDefinitionScopeChoices.ELIGIBILITY,
                expression={
                    "all": [
                        {"fact": "eligibility.latest.assessment_status", "operator": "equals", "value": "FINAL"},
                        {"fact": "eligibility.latest.result", "operator": "equals", "value": "ELIGIBLE"},
                        {"fact": "eligibility.latest.is_current", "operator": "equals", "value": True},
                    ]
                },
                actor_id=actor_id,
                now=now,
            ),
            "ELIGIBILITY_FINAL_NOT_ELIGIBLE": self._upsert_condition(
                study_id=study_id,
                study_version=study_version,
                code="ELIGIBILITY_FINAL_NOT_ELIGIBLE",
                scope=StudyConditionDefinitionScopeChoices.ELIGIBILITY,
                expression={
                    "all": [
                        {"fact": "eligibility.latest.assessment_status", "operator": "equals", "value": "FINAL"},
                        {"fact": "eligibility.latest.result", "operator": "equals", "value": "NOT_ELIGIBLE"},
                        {"fact": "eligibility.latest.is_current", "operator": "equals", "value": True},
                    ]
                },
                actor_id=actor_id,
                now=now,
            ),
        }

        self._upsert_transition(
            study_id=study_id,
            study_version=study_version,
            from_event=events["SCREENING"],
            to_event=events["ELIGIBILITY_ASSESSMENT"],
            condition=conditions["SCREENING_SOURCE_READY"],
            condition_scope=EventTransitionConditionScopeChoices.SUBJECT_EVENT,
            condition_code="screening_source_ready",
            actor_id=actor_id,
            now=now,
        )
        self._upsert_transition(
            study_id=study_id,
            study_version=study_version,
            from_event=events["ELIGIBILITY_ASSESSMENT"],
            to_event=events["ENROLLMENT"],
            condition=conditions["ELIGIBILITY_FINAL_ELIGIBLE"],
            condition_scope=EventTransitionConditionScopeChoices.ELIGIBILITY,
            condition_code="eligible",
            actor_id=actor_id,
            now=now,
        )
        if include_screen_failure:
            self._upsert_transition(
                study_id=study_id,
                study_version=study_version,
                from_event=events["ELIGIBILITY_ASSESSMENT"],
                to_event=events["SCREEN_FAILURE"],
                condition=conditions["ELIGIBILITY_FINAL_NOT_ELIGIBLE"],
                condition_scope=EventTransitionConditionScopeChoices.ELIGIBILITY,
                condition_code="not_eligible",
                actor_id=actor_id,
                now=now,
            )

        self.stdout.write(self.style.SUCCESS("Subject eligibility workflow seed completed."))

    def _upsert_event(self, *, study_id, study_version, code, name, event_type, timing_mode, event_category, execution_mode, sequence_no, is_required, actor_id, now):
        event, created = EventDefinition.objects.get_or_create(
            study_id=study_id,
            study_version=study_version,
            code=code,
            defaults={
                "created_at": now,
                "updated_at": now,
                "deleted": False,
                "name": name,
                "event_type": event_type,
                "timing_mode": timing_mode,
                "event_category": event_category,
                "execution_mode": execution_mode,
                "sequence_no": sequence_no,
                "is_required": is_required,
                "is_enabled": True,
                "created_by_id": actor_id,
                "updated_by_id": actor_id,
            },
        )
        if not created:
            for key, value in {
                "name": name,
                "event_type": event_type,
                "timing_mode": timing_mode,
                "event_category": event_category,
                "execution_mode": execution_mode,
                "sequence_no": sequence_no,
                "is_required": is_required,
                "is_enabled": True,
                "updated_at": now,
                "updated_by_id": actor_id,
            }.items():
                setattr(event, key, value)
            event.save()
        return event

    def _upsert_condition(self, *, study_id, study_version, code, scope, expression, actor_id, now):
        condition, created = ConditionDefinition.objects.get_or_create(
            study_id=study_id,
            study_version=study_version,
            code=code,
            defaults={
                "created_at": now,
                "updated_at": now,
                "deleted": False,
                "scope": scope,
                "expression_json": json.dumps(expression, ensure_ascii=True, sort_keys=True),
                "status": StudyConditionDefinitionStatusChoices.ACTIVE,
                "created_by_id": actor_id,
                "updated_by_id": actor_id,
            },
        )
        if not created:
            condition.scope = scope
            condition.expression_json = json.dumps(expression, ensure_ascii=True, sort_keys=True)
            condition.status = StudyConditionDefinitionStatusChoices.ACTIVE
            condition.updated_at = now
            condition.updated_by_id = actor_id
            condition.save()
        return condition

    def _upsert_transition(self, *, study_id, study_version, from_event, to_event, condition, condition_scope, condition_code, actor_id, now):
        rule, created = EventTransitionRule.objects.get_or_create(
            study_id=study_id,
            study_version=study_version,
            from_event_definition=from_event,
            to_event_definition=to_event,
            defaults={
                "created_at": now,
                "updated_at": now,
                "deleted": False,
                "transition_type": EventTransitionTypeChoices.CONDITIONAL,
                "condition_scope": condition_scope,
                "condition_code": condition_code,
                "condition_definition": condition,
                "auto_create": True,
                "auto_open": True,
                "requires_previous_completion": True,
                "allow_skip": False,
                "display_order": 1,
                "is_enabled": True,
                "created_by_id": actor_id,
                "updated_by_id": actor_id,
            },
        )
        if not created:
            rule.transition_type = EventTransitionTypeChoices.CONDITIONAL
            rule.condition_scope = condition_scope
            rule.condition_code = condition_code
            rule.condition_definition = condition
            rule.auto_create = True
            rule.auto_open = True
            rule.requires_previous_completion = True
            rule.allow_skip = False
            rule.is_enabled = True
            rule.updated_at = now
            rule.updated_by_id = actor_id
            rule.save()
        return rule
