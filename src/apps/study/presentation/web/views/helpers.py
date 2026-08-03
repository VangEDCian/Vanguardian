from apps.identity.infrastructure.persistence.models import StudyMembership
from apps.shared.navigation import user_can_access_permission


def _user_has_study_access(user, study_id):
    """Return True if the user is allowed to access the given study.

    Django superusers bypass scope filtering and can access all studies.
    All other users must have an active, non-deleted StudyMembership for the study.
    """
    if user.is_superuser:
        return True
    return StudyMembership.objects.filter(user=user, study_id=study_id, deleted=False).exists()


def _can_change_study_status(user, study_id):
    return user_can_access_permission(user, "study.change_study_status", study_id=study_id)


def _serialize_study_snapshot(study):
    return {
        "code": study.code,
        "name": study.name,
        "sponsor": study.sponsor,
        "description": study.description,
        "start_date": study.start_date.isoformat() if study.start_date else None,
        "end_date": study.end_date.isoformat() if study.end_date else None,
        "is_active": study.is_active,
        "subject_identifier_mode": study.subject_identifier_mode,
        "screening_identifier_mode": study.screening_identifier_mode,
        "subject_code_pattern": study.subject_code_pattern,
        "screening_code_pattern": study.screening_code_pattern,
        "subject_code_uniqueness_scope": study.subject_code_uniqueness_scope,
        "lock_subject_code_after_assignment": (
            study.lock_subject_code_after_assignment
        ),
    }
