from django.urls import path

from apps.subject.presentation.web.views import SubjectCreateView, SubjectDetailView, SubjectListView

app_name = "subject"

urlpatterns = [
    path(
        "studies/<int:study_id>/subjects/",
        SubjectListView.as_view(),
        name="subject_list",
    ),
    path(
        "studies/<int:study_id>/subjects/create/",
        SubjectCreateView.as_view(),
        name="subject_create",
    ),
    path(
        "studies/<int:study_id>/subjects/<int:subject_id>/",
        SubjectDetailView.as_view(),
        name="subject_detail",
    ),
]
