from apps.datacapture.infrastructure.repositories import DjangoDataCapturePageRepository


class DataCaptureSubjectSubmittedEditorMapService:

    def __init__(self, repository: DjangoDataCapturePageRepository | None = None):
        self._repository = repository or DjangoDataCapturePageRepository()

    def map_latest_submitted_entry_updated_by_id_by_subject_ids(
        self, *, subject_ids: tuple[int, ...]
    ) -> dict[int, int | None]:
        return self._repository.map_latest_submitted_entry_updated_by_id_by_subject_ids(
            subject_ids=subject_ids
        )
