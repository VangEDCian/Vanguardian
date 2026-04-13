from django.urls import path

from apps.subject.presentation.web.views import SubjectListView

app_name = "subject"

urlpatterns = [
    path(
        "studies/<int:study_id>/subjects/",
        SubjectListView.as_view(),
        name="subject_list",
    ),
]
