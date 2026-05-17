from apps.identity.infrastructure.persistence.models import StudyMembership


def _user_has_study_access(user, study_id):
    """Return True if the user is allowed to access the given study.

    Django superusers bypass scope filtering and can access all studies.
    All other users must have an active, non-deleted StudyMembership for the study.
    """
    if user.is_superuser:
        return True
    return StudyMembership.objects.filter(user=user, study_id=study_id, deleted=False).exists()


def _can_change_study_status(user):
    return user.has_perm("study.change_study_status")


def _serialize_study_snapshot(study):
    return {
        "code": study.code,
        "name": study.name,
        "sponsor": study.sponsor,
        "description": study.description,
        "start_date": study.start_date.isoformat() if study.start_date else None,
        "end_date": study.end_date.isoformat() if study.end_date else None,
        "is_active": study.is_active,
    }
