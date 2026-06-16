from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.datacapture.application import DataCaptureSaveSubmitPageService
from apps.datacapture.application.exceptions import DataCaptureValidationError
from apps.datacapture.presentation.web.mappers.save_submit import (
    save_page_command_from_post,
    submit_page_command_from_post,
)
from apps.identity.presentation.mixins import ContextPermissionRequiredMixin
from apps.subject.public import SubjectAbstractVerifyStudy


@method_decorator(csrf_exempt, name="dispatch")
class DataCaptureSaveView(LoginRequiredMixin, ContextPermissionRequiredMixin, SubjectAbstractVerifyStudy, View):
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
        return JsonResponse(
            {
                "entry_id": result.entry_id,
                "entry_status": result.entry_status,
                "page_status": result.page_status,
                "needs_confirmation": result.needs_confirmation,
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class DataCaptureSubmitView(LoginRequiredMixin, ContextPermissionRequiredMixin, SubjectAbstractVerifyStudy, View):
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
        return JsonResponse(
            {
                "entry_id": result.entry_id,
                "entry_status": result.entry_status,
                "page_status": result.page_status,
            }
        )
