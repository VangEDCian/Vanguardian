from apps.shared.application import ApplicationNotFoundError


class StudyNotFoundError(ApplicationNotFoundError):
    default_message = "Study was not found."


class SubjectEventInstanceNotFoundError(ApplicationNotFoundError):
    default_message = "Subject event instance was not found."


__all__ = ["StudyNotFoundError", "SubjectEventInstanceNotFoundError"]
