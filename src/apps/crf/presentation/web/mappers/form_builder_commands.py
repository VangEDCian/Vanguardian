from apps.crf.application.form_builder_orchestration import (
    SaveFieldAggregateCommand,
    UpdateFieldAggregateCommand,
)


def to_save_field_aggregate_command(**kwargs) -> SaveFieldAggregateCommand:
    return SaveFieldAggregateCommand(**kwargs)


def to_update_field_aggregate_command(**kwargs) -> UpdateFieldAggregateCommand:
    return UpdateFieldAggregateCommand(**kwargs)


__all__ = [
    "to_save_field_aggregate_command",
    "to_update_field_aggregate_command",
]
