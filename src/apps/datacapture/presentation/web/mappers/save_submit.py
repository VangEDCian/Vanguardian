from apps.datacapture.application import SavePageCommand, SubmitPageCommand


def save_page_command_from_post(
    *,
    subject_id: int,
    visit_id: int,
    crf_template_id: int,
    raw_body: str,
    actor_user_id: int | None,
) -> SavePageCommand:
    return SavePageCommand(
        subject_id=subject_id,
        visit_id=visit_id,
        crf_template_id=crf_template_id,
        data=raw_body,
        actor_user_id=actor_user_id,
    )


def submit_page_command_from_post(
    *,
    subject_id: int,
    visit_id: int,
    crf_template_id: int,
    raw_body: str,
    actor_user_id: int | None,
) -> SubmitPageCommand:
    return SubmitPageCommand(
        subject_id=subject_id,
        visit_id=visit_id,
        crf_template_id=crf_template_id,
        data=raw_body,
        actor_user_id=actor_user_id,
    )
