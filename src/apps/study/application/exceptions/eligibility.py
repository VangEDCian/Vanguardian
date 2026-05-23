from apps.shared.application import ApplicationNotFoundError, ApplicationValidationError


class EligibilityAssessmentError(ApplicationValidationError):
    default_message = "Eligibility assessment failed."


class EligibilityAssessmentNotFoundError(ApplicationNotFoundError):
    default_message = "Eligibility assessment was not found."


class EligibilityAssessmentPermissionError(ApplicationValidationError):
    default_message = "User does not have permission for eligibility assessment."


class EligibilityAssessmentRetractBlockedError(ApplicationValidationError):
    default_message = "Eligibility assessment retract is blocked."


class EligibilityEnrollmentGateError(ApplicationValidationError):
    default_message = "Subject does not have a final eligible assessment."


__all__ = [
    "EligibilityAssessmentError",
    "EligibilityAssessmentNotFoundError",
    "EligibilityAssessmentPermissionError",
    "EligibilityAssessmentRetractBlockedError",
    "EligibilityEnrollmentGateError",
]
