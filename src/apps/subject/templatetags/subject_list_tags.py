from django import template

register = template.Library()


@register.simple_tag
def subject_workflow_action_event_id(table, subject_id):
    event_id_by_subject_id = getattr(table, "workflow_action_event_id_by_subject_id", None) or {}
    return event_id_by_subject_id.get(subject_id)
