from django.urls import path

from apps.study.presentation.web.views import (
    StudyCreateView,
    StudyDetailView,
    StudyListView,
    StudyUpdateView,
)

app_name = "study"

urlpatterns = [
    path("studies", StudyListView.as_view(), name="study_list"),
    path("studies/new", StudyCreateView.as_view(), name="study_create"),
    path("studies/<int:study_id>", StudyDetailView.as_view(), name="study_detail"),
    path("studies/<int:study_id>/edit", StudyUpdateView.as_view(), name="study_update"),
]
