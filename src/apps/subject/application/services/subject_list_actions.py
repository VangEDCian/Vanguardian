from dataclasses import dataclass

from apps.subject.infrastructure.repositories.subject_list_actions import (
    DjangoSubjectListActionsRepository,
)


@dataclass(frozen=True)
class SubjectListActionSubjectDTO:
    pk: int
    study_id: int
    site_id: int
    subject_code: str
    screening_code: str


class SubjectListActionsQueryService:
    repository_class = DjangoSubjectListActionsRepository

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def get_subject(self, *, study_id: int, subject_id: int):
        return self.repository.get_subject(
            study_id=study_id,
            subject_id=subject_id,
            snapshot_class=SubjectListActionSubjectDTO,
        )


__all__ = [
    "SubjectListActionSubjectDTO",
    "SubjectListActionsQueryService",
]
