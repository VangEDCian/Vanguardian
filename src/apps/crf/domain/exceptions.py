class FormBuilderDomainValidationError(Exception):
    pass


class FormScopeViolationError(Exception):
    pass


class StudyScopeViolationError(Exception):
    pass


class FieldScopeViolationError(Exception):
    pass


class FieldKeyExistsError(Exception):
    pass
