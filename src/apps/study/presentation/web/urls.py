from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.urls import include, path

from apps.study.presentation.web.views import (
    SiteCreateView,
    SiteDeleteView,
    SiteDetailView,
    SiteListView,
    StudyCreateView,
    StudyCrfTemplateImportTemplateView,
    StudyCrfTemplateListView,
    StudyDeleteView,
    StudyDetailView,
    StudyEventDefinitionCreateView,
    StudyEventDefinitionImportTemplateView,
    StudyEventDefinitionListView,
    StudyEventFormBindingImportTemplateView,
    StudyListView,
    StudyRandomizationArmDeleteView,
    StudyRandomizationArmImportCommitView,
    StudyRandomizationArmImportPreviewView,
    StudyRandomizationSchemeDeleteView,
    StudyRandomizationSchemeImportCommitView,
    StudyRandomizationSchemeImportPreviewView,
    StudyRandomizationView,
    StudyToggleStatusView,
    StudyUpdateView,
)

app_name = "study"


def _superuser_guard(view):
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), "/login/", "next")
        if not request.user.is_superuser:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped

urlpatterns = [
    path("studies", _superuser_guard(StudyListView.as_view()), name="study_list"),
    path("studies/new", _superuser_guard(StudyCreateView.as_view()), name="study_create"),
    path("studies/<int:study_id>", _superuser_guard(StudyDetailView.as_view()), name="study_detail"),
    path("studies/<int:study_id>/crftemplates/import", _superuser_guard(StudyCrfTemplateImportTemplateView.as_view()), name="study_crf_template_import"),
    path("studies/<int:study_id>/crftemplates", _superuser_guard(StudyCrfTemplateListView.as_view()), name="study_crf_templates"),
    path("studies/<int:study_id>/eventdefinitions/bindingforms/import", _superuser_guard(StudyEventFormBindingImportTemplateView.as_view()), name="study_event_form_binding_import"),
    path("studies/<int:study_id>/eventdefinitions/import", _superuser_guard(StudyEventDefinitionImportTemplateView.as_view()), name="study_event_definition_import"),
    path("studies/<int:study_id>/eventdefinitions/new", _superuser_guard(StudyEventDefinitionCreateView.as_view()), name="study_event_definition_create"),
    path("studies/<int:study_id>/eventdefinitions", _superuser_guard(StudyEventDefinitionListView.as_view()), name="study_event_definitions"),
    path("studies/<int:study_id>/randomization", _superuser_guard(StudyRandomizationView.as_view()), name="study_randomization"),
    path("studies/<int:study_id>/delete", _superuser_guard(StudyDeleteView.as_view()), name="study_delete"),
    path("studies/<int:study_id>/edit", _superuser_guard(StudyUpdateView.as_view()), name="study_update"),
    path(
        "studies/<int:study_id>/toggle-status", _superuser_guard(StudyToggleStatusView.as_view()),
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
                    _superuser_guard(StudyRandomizationSchemeImportPreviewView.as_view()),
                    name="study_randomization_scheme_import_preview",
                ),
                path(
                    "schemes/import/commit",
                    _superuser_guard(StudyRandomizationSchemeImportCommitView.as_view()),
                    name="study_randomization_scheme_import_commit",
                ),
                path(
                    "schemes/<int:scheme_id>/delete",
                    _superuser_guard(StudyRandomizationSchemeDeleteView.as_view()),
                    name="study_randomization_scheme_delete",
                ),
                path(
                    "arms/import/preview",
                    _superuser_guard(StudyRandomizationArmImportPreviewView.as_view()),
                    name="study_randomization_arm_import_preview",
                ),
                path(
                    "arms/import/commit",
                    _superuser_guard(StudyRandomizationArmImportCommitView.as_view()),
                    name="study_randomization_arm_import_commit",
                ),
                path(
                    "arms/<int:arm_id>/delete",
                    _superuser_guard(StudyRandomizationArmDeleteView.as_view()),
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
                path("", _superuser_guard(SiteListView.as_view()), name="site_list"),
                path("new", _superuser_guard(SiteCreateView.as_view()), name="site_create"),
                path("<int:site_id>", _superuser_guard(SiteDetailView.as_view()), name="site_detail"),
                path("<int:site_id>/delete", _superuser_guard(SiteDeleteView.as_view()), name="site_delete"),
            ],
        ),
    ),
]
