from django.urls import path

from apps.datacapture.presentation.web.views import DataCaptureSaveView, DataCaptureSubmitView

app_name = "datacapture"

urlpatterns = [
    path(
        "studies/<int:study_id>/subjects/<int:subject_id>/events/<int:visit_id>/forms/<int:crf_template_id>/save/",
        DataCaptureSaveView.as_view(),
        name="page_save",
    ),
    path(
        "studies/<int:study_id>/subjects/<int:subject_id>/events/<int:visit_id>/forms/<int:crf_template_id>/submit/",
        DataCaptureSubmitView.as_view(),
        name="page_submit",
    ),
]
