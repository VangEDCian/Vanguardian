from django.urls import path

from apps.subject.presentation.web.views import (
    SubjectCreateView,
    SubjectDetailView,
    SubjectEventInstanceFileContentView,
    SubjectEventInstanceFileImportView,
    SubjectEventInstanceFilePreviewView,
    SubjectListView,
)
from apps.subject.presentation.web.views.verification_verify_checked import (
    SubjectFormVerificationReopenView,
    SubjectFormVerificationVerifyCheckedView,
)

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
        "studies/<int:study_id>/subjects/<int:subject_id>/events/<int:visit_id>/forms/<int:crf_template_id>/verification/verify-checked/",
        SubjectFormVerificationVerifyCheckedView.as_view(),
        name="subject_form_verification_verify_checked",
    ),
    path(
        "studies/<int:study_id>/subjects/<int:subject_id>/events/<int:visit_id>/forms/<int:crf_template_id>/verification/reopen/",
        SubjectFormVerificationReopenView.as_view(),
        name="subject_form_verification_reopen",
    ),
    path(
        "studies/<int:study_id>/subjects/<int:subject_id>/",
        SubjectDetailView.as_view(),
        name="subject_detail",
    ),
    path(
        "studies/<int:study_id>/subjects/<int:subject_id>/events/<int:event_instance_id>/files/import/",
        SubjectEventInstanceFileImportView.as_view(),
        name="subject_eventinstance_file_import",
    ),
    path(
        "studies/<int:study_id>/subjects/<int:subject_id>/events/<int:event_instance_id>/files/",
        SubjectEventInstanceFilePreviewView.as_view(),
        name="subject_eventinstance_file_preview",
    ),
    path(
        "studies/<int:study_id>/subjects/<int:subject_id>/events/<int:event_instance_id>/files/<int:file_id>/content/",
        SubjectEventInstanceFileContentView.as_view(),
        name="subject_eventinstance_file_content",
    ),
]
