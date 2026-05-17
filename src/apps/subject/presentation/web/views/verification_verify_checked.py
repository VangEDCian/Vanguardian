from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.datacapture.application.exceptions import DataCaptureValidationError
from apps.datacapture.public import (
    merge_form_verification_checked_fields_into_page_state_final_data,
    reopen_verified_form_verification_page_state,
)
from apps.subject.application import (
    SubjectFormVerificationRequestValidator,
    SubjectValidationError,
)
from apps.subject.public import SubjectAbstractVerifyStudy


@method_decorator(csrf_exempt, name="dispatch")
class SubjectFormVerificationVerifyCheckedView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SubjectAbstractVerifyStudy,
    View,
):
    permission_required = "subject.verify_form"
    raise_exception = True

    def post(self, request, *args, **kwargs):
        try:
            normalized = SubjectFormVerificationRequestValidator.parse_checked_field_template_ids(
                request.body
            )
            all_verified, page_status, blocking_reasons = merge_form_verification_checked_fields_into_page_state_final_data(
                subject_id=int(kwargs["subject_id"]),
                visit_id=int(kwargs["visit_id"]),
                crf_template_id=int(kwargs["crf_template_id"]),
                checked_field_template_ids=normalized,
                actor_user_id=getattr(request.user, "id", None),
            )
        except (SubjectValidationError, DataCaptureValidationError) as exc:
            return JsonResponse({"error": list(exc.messages)}, status=400)
        return JsonResponse(
            {
                "ok": True,
                "field_template_ids": normalized,
                "all_verified": all_verified,
                "page_status": page_status,
                "blocking_reasons": blocking_reasons,
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class SubjectFormVerificationReopenView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SubjectAbstractVerifyStudy,
    View,
):
    permission_required = "subject.verify_form"
    raise_exception = True

    def post(self, request, *args, **kwargs):
        try:
            reason_text = SubjectFormVerificationRequestValidator.parse_reopen_reason_text(
                request.body
            )
            page_status = reopen_verified_form_verification_page_state(
                subject_id=int(kwargs["subject_id"]),
                visit_id=int(kwargs["visit_id"]),
                crf_template_id=int(kwargs["crf_template_id"]),
                reason_text=reason_text,
                actor_user_id=getattr(request.user, "id", None),
            )
        except (SubjectValidationError, DataCaptureValidationError) as exc:
            return JsonResponse({"error": list(exc.messages)}, status=400)
        return JsonResponse(
            {
                "ok": True,
                "page_status": page_status,
            }
        )


__all__ = ["SubjectFormVerificationReopenView", "SubjectFormVerificationVerifyCheckedView"]
