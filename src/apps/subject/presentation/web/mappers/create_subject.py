from apps.subject.application.commands.create_subject import CreateSubjectCommand


def to_create_subject_command(
    *,
    study_id: int,
    site_id: int,
    actor_user_id: int,
    subject_code: str | None = None,
    screening_code: str | None = None,
) -> CreateSubjectCommand:
    return CreateSubjectCommand(
        study_id=study_id,
        site_id=site_id,
        actor_user_id=actor_user_id,
        subject_code=subject_code,
        screening_code=screening_code,
    )


__all__ = ["to_create_subject_command"]
