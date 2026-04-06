from django.urls import path, include

from apps.study.presentation.web.views import (
    StudyCreateView,
    StudyDeleteView,
    StudyDetailView,
    StudyListView,
    StudyToggleStatusView,
    StudyUpdateView,
)

app_name = "study"

urlpatterns = [
    path("studies/sites/", include("apps.study.presentation.web.site.urls")),

    path("studies", StudyListView.as_view(), name="study_list"),
    path("studies/new", StudyCreateView.as_view(), name="study_create"),
    path("studies/<int:study_id>", StudyDetailView.as_view(), name="study_detail"),
    path("studies/<int:study_id>/delete", StudyDeleteView.as_view(), name="study_delete"),
    path("studies/<int:study_id>/edit", StudyUpdateView.as_view(), name="study_update"),
    path("studies/<int:study_id>/toggle-status", StudyToggleStatusView.as_view(), name="study_toggle_status"),
]
