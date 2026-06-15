from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.datacapture.application import DataCaptureSaveSubmitPageService
from apps.datacapture.application.exceptions import DataCaptureValidationError
from apps.datacapture.application.services.page_entry_read import DataCapturePageEntryReadService
from apps.identity.presentation.mixins import ContextPermissionRequiredMixin
from apps.datacapture.presentation.api.mappers.save_submit import (
    delete_draft_page_command_from_post,
    save_page_command_from_post,
    submit_page_command_from_post,
)
from apps.subject.public import SubjectAbstractVerifyStudy


def _latest_active_entry_payload(*, subject_id: int, visit_id: int, crf_template_id: int):
    latest = DataCapturePageEntryReadService().get_latest_active_page_entry(
        subject_id=subject_id,
        visit_id=visit_id,
        crf_template_id=crf_template_id,
    )
    if latest is None:
        return None
    return {
        "id": latest.id,
        "entry_no": latest.entry_no,
        "entry_version": latest.entry_version,
        "status": latest.status,
    }


@method_decorator(csrf_exempt, name="dispatch")
class DataCaptureSaveAPIView(LoginRequiredMixin, ContextPermissionRequiredMixin, SubjectAbstractVerifyStudy, View):
    permission_required = "subject.view_subject_detail"
    authorization_scope = "STUDY_SITE"
    require_site_context = True
    raise_exception = True

    def post(self, request, *args, **kwargs):
        try:
            result = DataCaptureSaveSubmitPageService().save(
                save_page_command_from_post(
                    subject_id=kwargs["subject_id"],
                    visit_id=kwargs["visit_id"],
                    crf_template_id=kwargs["crf_template_id"],
                    raw_body=request.body.decode("utf-8"),
                    actor_user_id=getattr(request.user, "id", None),
                )
            )
        except DataCaptureValidationError as exc:
            return JsonResponse({"error": list(exc.messages)}, status=400)
        latest_page_entry = _latest_active_entry_payload(
            subject_id=kwargs["subject_id"],
            visit_id=kwargs["visit_id"],
            crf_template_id=kwargs["crf_template_id"],
        )
        return JsonResponse(
            {
                "entry_id": result.entry_id,
                "entry_status": result.entry_status,
                "page_status": result.page_status,
                "needs_confirmation": result.needs_confirmation,
                "created_new_entry": result.created_new_entry,
                "latest_page_entry": latest_page_entry,
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class DataCaptureSubmitAPIView(LoginRequiredMixin, ContextPermissionRequiredMixin, SubjectAbstractVerifyStudy, View):
    permission_required = "subject.view_subject_detail"
    authorization_scope = "STUDY_SITE"
    require_site_context = True
    raise_exception = True

    def post(self, request, *args, **kwargs):
        try:
            result = DataCaptureSaveSubmitPageService().submit(
                submit_page_command_from_post(
                    subject_id=kwargs["subject_id"],
                    visit_id=kwargs["visit_id"],
                    crf_template_id=kwargs["crf_template_id"],
                    raw_body=request.body.decode("utf-8"),
                    actor_user_id=getattr(request.user, "id", None),
                )
            )
        except DataCaptureValidationError as exc:
            return JsonResponse({"error": list(exc.messages)}, status=400)
        latest_page_entry = _latest_active_entry_payload(
            subject_id=kwargs["subject_id"],
            visit_id=kwargs["visit_id"],
            crf_template_id=kwargs["crf_template_id"],
        )
        return JsonResponse(
            {
                "entry_id": result.entry_id,
                "entry_status": result.entry_status,
                "page_status": result.page_status,
                "created_new_entry": result.created_new_entry,
                "latest_page_entry": latest_page_entry,
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class DataCaptureDeleteDraftAPIView(LoginRequiredMixin, ContextPermissionRequiredMixin, SubjectAbstractVerifyStudy, View):
    permission_required = "subject.view_subject_detail"
    authorization_scope = "STUDY_SITE"
    require_site_context = True
    raise_exception = True

    def post(self, request, *args, **kwargs):
        try:
            result = DataCaptureSaveSubmitPageService().delete_latest_draft(
                delete_draft_page_command_from_post(
                    subject_id=kwargs["subject_id"],
                    visit_id=kwargs["visit_id"],
                    crf_template_id=kwargs["crf_template_id"],
                    actor_user_id=getattr(request.user, "id", None),
                )
            )
        except DataCaptureValidationError as exc:
            return JsonResponse({"error": list(exc.messages)}, status=400)
        return JsonResponse(
            {
                "entry_id": result.entry_id,
                "entry_status": result.entry_status,
                "page_status": result.page_status,
            }
        )
