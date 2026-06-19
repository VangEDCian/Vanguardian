from django.urls import path

from apps.datacapture.presentation.api.views import (
    DataCaptureDeleteDraftAPIView,
    DataCaptureFormInstanceListCreateAPIView,
    DataCaptureSaveAPIView,
    DataCaptureSubmitAPIView,
)

app_name = "datacapture"

urlpatterns = [
    path(
        "studies/<int:study_id>/subjects/<int:subject_id>/events/<int:visit_id>/form-instances/",
        DataCaptureFormInstanceListCreateAPIView.as_view(),
        name="form_instances",
    ),
    path(
        "studies/<int:study_id>/subjects/<int:subject_id>/events/<int:visit_id>/forms/<int:crf_template_id>/save/",
        DataCaptureSaveAPIView.as_view(),
        name="page_save",
    ),
    path(
        "studies/<int:study_id>/subjects/<int:subject_id>/events/<int:visit_id>/forms/<int:crf_template_id>/submit/",
        DataCaptureSubmitAPIView.as_view(),
        name="page_submit",
    ),
    path(
        "studies/<int:study_id>/subjects/<int:subject_id>/events/<int:visit_id>/forms/<int:crf_template_id>/delete-draft/",
        DataCaptureDeleteDraftAPIView.as_view(),
        name="page_delete_draft",
    ),
]
