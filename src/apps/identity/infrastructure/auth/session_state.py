from django.utils import timezone


def activate_single_active_session(user, session):
    if not _can_track_user_session(user) or not hasattr(user.__class__, "objects"):
        return

    session_key = _ensure_session_key(session)
    if not session_key:
        return

    user.__class__.objects.filter(pk=user.pk).update(
        active_session_key=session_key,
        active_session_started_at=timezone.now(),
    )
    user.active_session_key = session_key


def clear_single_active_session(user, session):
    if not _can_track_user_session(user) or not hasattr(user.__class__, "objects"):
        return

    current_session_key = getattr(session, "session_key", "") or ""
    if current_session_key and getattr(user, "active_session_key", "") != current_session_key:
        return

    user.__class__.objects.filter(pk=user.pk).update(
        active_session_key="",
        active_session_started_at=None,
    )
    user.active_session_key = ""


def is_single_active_session_valid(request):
    user = getattr(request, "user", None)
    if not _can_track_user_session(user):
        return True

    active_session_key = getattr(user, "active_session_key", "") or ""
    if not active_session_key:
        return True

    current_session_key = getattr(getattr(request, "session", None), "session_key", "") or ""
    return bool(current_session_key and current_session_key == active_session_key)


def _can_track_user_session(user):
    return (
        user is not None
        and getattr(user, "is_authenticated", False)
        and getattr(user, "pk", None)
        and hasattr(user, "active_session_key")
    )


def _ensure_session_key(session):
    if session is None:
        return ""

    session_key = getattr(session, "session_key", "") or ""
    if session_key:
        return session_key

    save = getattr(session, "save", None)
    if callable(save):
        save()
    return getattr(session, "session_key", "") or ""
