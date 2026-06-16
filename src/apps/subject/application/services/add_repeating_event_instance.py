from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.core.choices import EventInstanceStatusChoices
from apps.subject.application.exceptions import SubjectValidationError
from apps.subject.infrastructure.repositories import DjangoSubjectRepeatingEventInstanceRepository


class AddRepeatingSubjectEventInstanceError(SubjectValidationError):
    default_message = _("Unable to add another subject event instance.")


class RepeatingEventDefinitionNotAvailableError(AddRepeatingSubjectEventInstanceError):
    default_message = _("Repeating event definition was not found.")


class CurrentRepeatingEventOpenError(AddRepeatingSubjectEventInstanceError):
    default_message = _("Complete the current form before creating another one.")


class MaxRepeatingEventInstancesExceededError(AddRepeatingSubjectEventInstanceError):
    default_message = _("You have exceeded the allowed number of forms. Please contact the Administrator.")


class AddRepeatingSubjectEventInstanceService:
    repository_class = DjangoSubjectRepeatingEventInstanceRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def execute(
        self,
        *,
        study_id: int,
        subject_id: int,
        event_definition_id: int,
        actor_user_id: int | None,
    ):
        with transaction.atomic():
            return self._execute(
                study_id=study_id,
                subject_id=subject_id,
                event_definition_id=event_definition_id,
                actor_user_id=actor_user_id,
            )

    def _execute(
        self,
        *,
        study_id: int,
        subject_id: int,
        event_definition_id: int,
        actor_user_id: int | None,
    ):
        subject = self.repository.get_subject_for_update(
            study_id=study_id,
            subject_id=subject_id,
        )
        event_definition = self.repository.get_repeating_event_definition_for_update(
            study_id=study_id,
            event_definition_id=event_definition_id,
        )
        if subject is None or event_definition is None:
            raise RepeatingEventDefinitionNotAvailableError()

        existing_instances = self.repository.list_event_instances_for_update(
            subject_id=subject.id,
            event_definition_id=event_definition.id,
        )
        if any(event.status == EventInstanceStatusChoices.OPEN for event in existing_instances):
            raise CurrentRepeatingEventOpenError()
        if (
            event_definition.max_repeats is not None
            and len(existing_instances) >= event_definition.max_repeats
        ):
            raise MaxRepeatingEventInstancesExceededError()

        next_repeat_index = self.repository.get_next_repeat_index(
            subject_id=subject.id,
            event_definition_id=event_definition.id,
        )
        return self.repository.create_open_repeating_event_instance(
            subject=subject,
            event_definition=event_definition,
            repeat_index=next_repeat_index,
            actor_user_id=actor_user_id,
            now=self.repository.now(),
        )


__all__ = [
    "AddRepeatingSubjectEventInstanceError",
    "AddRepeatingSubjectEventInstanceService",
    "CurrentRepeatingEventOpenError",
    "MaxRepeatingEventInstancesExceededError",
    "RepeatingEventDefinitionNotAvailableError",
]
