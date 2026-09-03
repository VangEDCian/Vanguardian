from apps.datacapture.infrastructure.repositories import DjangoDataCapturePageRepository


class DataCapturePageStateWriteService:

    def __init__(self, repository=None):
        self.repository = repository or DjangoDataCapturePageRepository()

    def ensure_open_if_not_exists(
        self,
        *,
        subject_id: int,
        visit_id: int,
        crf_template_id: int,
        actor_user_id: int | None = None,
        event_form_binding_id: int | None = None,
    ) -> bool:
        return self.repository.ensure_open_page_state_if_not_exists(
            subject_id=subject_id,
            visit_id=visit_id,
            crf_template_id=crf_template_id,
            actor_user_id=actor_user_id,
            event_form_binding_id=event_form_binding_id,
        )

    def ensure_draft_if_not_exists(self, **kwargs) -> bool:
        return self.ensure_open_if_not_exists(**kwargs)
