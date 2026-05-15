from apps.subject.application.exceptions.base import SubjectValidationError


class SubjectFormVerificationInvalidJsonError(SubjectValidationError):
    default_message = "Invalid JSON"


class SubjectFormVerificationFieldTemplateIdsTypeError(SubjectValidationError):
    default_message = "field_template_ids must be a list"


class SubjectFormVerificationFieldTemplateIdsValueError(SubjectValidationError):
    default_message = "field_template_ids must contain integers"


__all__ = [
    "SubjectFormVerificationFieldTemplateIdsTypeError",
    "SubjectFormVerificationFieldTemplateIdsValueError",
    "SubjectFormVerificationInvalidJsonError",
]
