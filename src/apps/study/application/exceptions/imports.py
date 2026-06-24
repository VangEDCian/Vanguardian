from django.utils.translation import gettext_lazy as _

from apps.shared.application import ApplicationValidationError


class StudyImportTemplateError(ApplicationValidationError):
    """Base error raised for study workbook import failures."""


class CrfTemplateImportTemplateError(StudyImportTemplateError):
    """Base error raised for CRF template import failures."""


class CrfTemplateImportDependencyError(CrfTemplateImportTemplateError):
    """Raised when the Excel parser dependency is missing."""


class CrfTemplateImportFormatError(CrfTemplateImportTemplateError):
    """Raised when the uploaded workbook shape is invalid."""


class EventDefinitionImportTemplateError(StudyImportTemplateError):
    """Base error raised for event definition template import failures."""


class EventDefinitionImportDependencyError(EventDefinitionImportTemplateError):
    """Raised when the Excel parser dependency is missing."""


class EventDefinitionImportFormatError(EventDefinitionImportTemplateError):
    """Raised when the uploaded workbook shape is invalid."""


class EventFormBindingImportTemplateError(StudyImportTemplateError):
    """Base error raised for event form binding template import failures."""


class EventFormBindingImportDependencyError(EventFormBindingImportTemplateError):
    """Raised when the Excel parser dependency is missing."""


class EventFormBindingImportFormatError(EventFormBindingImportTemplateError):
    """Raised when the uploaded workbook shape is invalid."""


class FactMappingImportTemplateError(StudyImportTemplateError):
    """Base error raised for fact mapping template import failures."""


class FactMappingImportDependencyError(FactMappingImportTemplateError):
    """Raised when the Excel parser dependency is missing."""


class FactMappingImportFormatError(FactMappingImportTemplateError):
    """Raised when the uploaded workbook shape is invalid."""


class EventAttestationPolicyImportTemplateError(StudyImportTemplateError):
    """Base error raised for event attestation policy import failures."""


class EventAttestationPolicyImportDependencyError(EventAttestationPolicyImportTemplateError):
    """Raised when the Excel parser dependency is missing."""


class EventAttestationPolicyImportFormatError(EventAttestationPolicyImportTemplateError):
    """Raised when the uploaded workbook shape is invalid."""


class RandomizationImportUseCaseError(ApplicationValidationError):
    """Base exception for randomization import application use cases."""

    default_message = "Randomization import failed."


class RandomizationImportDependencyError(RandomizationImportUseCaseError):
    """Raised when a workbook parser dependency is unavailable."""


class RandomizationImportFormatError(RandomizationImportUseCaseError):
    """Raised when the uploaded import file structure is invalid."""


class RandomizationImportValidationError(RandomizationImportUseCaseError):
    """Raised when the uploaded file contains row-level validation issues."""

    def __init__(self, issues):
        self.message = str(_("The uploaded file contains validation issues."))
        self.issues = issues
        super().__init__(self.message)


__all__ = [
    "CrfTemplateImportDependencyError",
    "CrfTemplateImportFormatError",
    "CrfTemplateImportTemplateError",
    "EventAttestationPolicyImportDependencyError",
    "EventAttestationPolicyImportFormatError",
    "EventAttestationPolicyImportTemplateError",
    "EventDefinitionImportDependencyError",
    "EventDefinitionImportFormatError",
    "EventDefinitionImportTemplateError",
    "EventFormBindingImportDependencyError",
    "EventFormBindingImportFormatError",
    "EventFormBindingImportTemplateError",
    "FactMappingImportDependencyError",
    "FactMappingImportFormatError",
    "FactMappingImportTemplateError",
    "RandomizationImportDependencyError",
    "RandomizationImportFormatError",
    "RandomizationImportUseCaseError",
    "RandomizationImportValidationError",
    "StudyImportTemplateError",
]
