from django import template

register = template.Library()


@register.simple_tag
def subject_workflow_action_event_id(table, subject_id):
    event_id_by_subject_id = getattr(table, "workflow_action_event_id_by_subject_id", None) or {}
    return event_id_by_subject_id.get(subject_id)


@register.simple_tag
def subject_can_update_subject(table, perms):
    table_permission = getattr(table, "can_update_subject", None)
    if table_permission is not None:
        return bool(table_permission)

    subject_perms = _lookup_template_value(perms, "subject")
    return bool(_lookup_template_value(subject_perms, "update_subject"))


def _lookup_template_value(value, key):
    if value is None:
        return None
    if isinstance(value, dict):
        return value.get(key)
    try:
        return value[key]
    except (AttributeError, KeyError, TypeError):
        return getattr(value, key, None)
