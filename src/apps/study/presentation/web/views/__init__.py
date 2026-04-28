from apps.study.presentation.web.views.crf_templates import (
    StudyCrfTemplateImportTemplateView,
    StudyCrfTemplateListView,
)
from apps.study.presentation.web.views.eventdefinitions import (
    StudyEventDefinitionCreateView,
    StudyEventDefinitionImportTemplateView,
    StudyEventDefinitionListView,
    StudyEventFormBindingImportTemplateView,
)
from apps.study.presentation.web.views.randomization import (
    StudyRandomizationArmImportCommitView,
    StudyRandomizationArmImportPreviewView,
    StudyRandomizationSchemeImportCommitView,
    StudyRandomizationSchemeImportPreviewView,
    StudyRandomizationView,
)
from apps.study.presentation.web.views.randomization_deletes import (
    StudyRandomizationArmDeleteView,
    StudyRandomizationSchemeDeleteView,
)
from apps.study.presentation.web.views.site import (
    SiteCreateView,
    SiteDeleteView,
    SiteDetailView,
    SiteListView,
)
from apps.study.presentation.web.views.studies import (
    StudyDetailView,
    StudyListView,
)
from apps.study.presentation.web.views.study_actions import (
    StudyCreateView,
    StudyDeleteView,
    StudyToggleStatusView,
    StudyUpdateView,
)

__all__ = [
    "SiteCreateView",
    "SiteDeleteView",
    "SiteDetailView",
    "SiteListView",
    "StudyCreateView",
    "StudyCrfTemplateImportTemplateView",
    "StudyCrfTemplateListView",
    "StudyDeleteView",
    "StudyDetailView",
    "StudyEventDefinitionCreateView",
    "StudyEventDefinitionImportTemplateView",
    "StudyEventDefinitionListView",
    "StudyEventFormBindingImportTemplateView",
    "StudyListView",
    "StudyRandomizationArmDeleteView",
    "StudyRandomizationArmImportCommitView",
    "StudyRandomizationArmImportPreviewView",
    "StudyRandomizationSchemeDeleteView",
    "StudyRandomizationSchemeImportCommitView",
    "StudyRandomizationSchemeImportPreviewView",
    "StudyRandomizationView",
    "StudyToggleStatusView",
    "StudyUpdateView",
]
