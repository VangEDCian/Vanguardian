from django.urls import path, include

from apps.study.presentation.web.views import (
    StudyRandomizationArmDeleteView,
    StudyRandomizationArmImportCommitView,
    StudyRandomizationArmImportPreviewView,
    StudyCreateView,
    StudyCrfTemplateImportTemplateView,
    StudyCrfTemplateListView,
    StudyEventDefinitionCreateView,
    StudyEventFormBindingImportTemplateView,
    StudyEventDefinitionImportTemplateView,
    StudyEventDefinitionListView,
    StudyRandomizationSchemeDeleteView,
    StudyRandomizationSchemeImportCommitView,
    StudyRandomizationSchemeImportPreviewView,
    StudyRandomizationView,
    StudyDeleteView,
    StudyDetailView,
    StudyListView,
    StudyToggleStatusView,
    StudyUpdateView,

    SiteListView,
    SiteDetailView,
    SiteCreateView,
    SiteDeleteView,
)

app_name = "study"

urlpatterns = [
    path("studies", StudyListView.as_view(), name="study_list"),
    path("studies/new", StudyCreateView.as_view(), name="study_create"),
    path("studies/<int:study_id>", StudyDetailView.as_view(), name="study_detail"),
    path("studies/<int:study_id>/crftemplates/import", StudyCrfTemplateImportTemplateView.as_view(), name="study_crf_template_import"),
    path("studies/<int:study_id>/crftemplates", StudyCrfTemplateListView.as_view(), name="study_crf_templates"),
    path("studies/<int:study_id>/eventdefinitions/bindingforms/import", StudyEventFormBindingImportTemplateView.as_view(), name="study_event_form_binding_import"),
    path("studies/<int:study_id>/eventdefinitions/import", StudyEventDefinitionImportTemplateView.as_view(), name="study_event_definition_import"),
    path("studies/<int:study_id>/eventdefinitions/new", StudyEventDefinitionCreateView.as_view(), name="study_event_definition_create"),
    path("studies/<int:study_id>/eventdefinitions", StudyEventDefinitionListView.as_view(), name="study_event_definitions"),
    path("studies/<int:study_id>/randomization", StudyRandomizationView.as_view(), name="study_randomization"),
    path("studies/<int:study_id>/delete", StudyDeleteView.as_view(), name="study_delete"),
    path("studies/<int:study_id>/edit", StudyUpdateView.as_view(), name="study_update"),
    path(
        "studies/<int:study_id>/toggle-status", StudyToggleStatusView.as_view(),
        name="study_toggle_status",
    ),
]

# Study.Randomization
urlpatterns += [
    path(
        "studies/<int:study_id>/randomization/", include(
            [
                path(
                    "schemes/import/preview",
                    StudyRandomizationSchemeImportPreviewView.as_view(),
                    name="study_randomization_scheme_import_preview",
                ),
                path(
                    "schemes/import/commit",
                    StudyRandomizationSchemeImportCommitView.as_view(),
                    name="study_randomization_scheme_import_commit",
                ),
                path(
                    "schemes/<int:scheme_id>/delete",
                    StudyRandomizationSchemeDeleteView.as_view(),
                    name="study_randomization_scheme_delete",
                ),
                path(
                    "arms/import/preview",
                    StudyRandomizationArmImportPreviewView.as_view(),
                    name="study_randomization_arm_import_preview",
                ),
                path(
                    "arms/import/commit",
                    StudyRandomizationArmImportCommitView.as_view(),
                    name="study_randomization_arm_import_commit",
                ),
                path(
                    "arms/<int:arm_id>/delete",
                    StudyRandomizationArmDeleteView.as_view(),
                    name="study_randomization_arm_delete",
                ),
            ],
        ),
    ),
]


# Study.Site
urlpatterns += [
    path(
        "studies/<int:study_id>/sites/", include(
            [
                path("", SiteListView.as_view(), name="site_list"),
                path("new", SiteCreateView.as_view(), name="site_create"),
                path("<int:site_id>", SiteDetailView.as_view(), name="site_detail"),
                path("<int:site_id>/delete", SiteDeleteView.as_view(), name="site_delete"),
            ],
        ),
    ),
]
