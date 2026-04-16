from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone

from apps.study.models import Study
from apps.study.application.services.study_subject_code_generation import (
    StudySubjectCodeGenerationService,
)
from apps.subject.models import Subject


class StudyNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class CreateSubjectCommand:
    study_id: int
    site_id: int
    actor_user_id: int


class CreateSubjectService:
    def execute(self, command: CreateSubjectCommand) -> Subject:
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                with transaction.atomic():
                    return self._create_once(command=command)
            except IntegrityError:
                if attempt == max_retries:
                    raise

        raise RuntimeError("Unexpected subject creation retry flow.")

    @staticmethod
    def _create_once(command: CreateSubjectCommand) -> Subject:
        study = (
            Study.objects.select_for_update()
            .filter(pk=command.study_id, deleted=False)
            .only("id", "code")
            .first()
        )
        if study is None:
            raise StudyNotFoundError(command.study_id)

        max_current_sequence = Subject.objects.filter(study_id=command.study_id).aggregate(
            max_current_sequence=Max("current_sequence"),
        )["max_current_sequence"] or 0
        next_current_sequence = max_current_sequence + 1
        generated_codes = StudySubjectCodeGenerationService().generate(
            study_code=study.code,
            current_sequence=next_current_sequence,
        )
        now = timezone.now()
        return Subject.objects.create(
            subject_code=generated_codes.subject_code,
            screening_code=generated_codes.screening_code,
            current_sequence=next_current_sequence,
            site_id=command.site_id,
            study_id=command.study_id,
            created_at=now,
            updated_at=now,
            created_by_id=command.actor_user_id,
            updated_by_id=command.actor_user_id,
        )
