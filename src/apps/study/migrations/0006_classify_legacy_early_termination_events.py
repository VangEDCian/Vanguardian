from django.db import migrations
from django.db.models import Q


def classify_legacy_early_termination_events(apps, schema_editor):
    event_definition = apps.get_model("study", "EventDefinition")
    event_transition_rule = apps.get_model("study", "EventTransitionRule")

    legacy_targets = event_definition.objects.filter(deleted=False).filter(
        Q(code__iexact="ET") | Q(name__iexact="Early Termination")
    )
    target_ids = list(legacy_targets.values_list("id", flat=True))
    legacy_targets.update(
        event_category="eos",
        timing_mode="conditional",
        lifecycle_role="early_termination",
    )
    if target_ids:
        event_transition_rule.objects.filter(
            deleted=False,
            to_event_definition_id__in=target_ids,
        ).update(
            transition_type="conditional",
            condition_scope="subject",
            condition_code="early_termination.requested",
            auto_open=True,
            requires_previous_completion=False,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("study", "0005_eventdefinition_lifecycle_role"),
    ]

    operations = [
        migrations.RunPython(
            classify_legacy_early_termination_events,
            migrations.RunPython.noop,
        ),
    ]
