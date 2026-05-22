from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.datacapture.application.exceptions import DataCaptureValidationError
from apps.datacapture.domain import DataCapturePageState
from apps.datacapture.public import (
    get_latest_submitted_page_entry_for_subject_visit_crf,
    get_page_state_id_for_subject_visit_crf,
    get_page_state_status_for_subject_visit_crf,
    is_field_verified_for_page_state,
    merge_form_verification_checked_fields_into_page_state_final_data,
    reopen_verified_form_verification_page_state,
)
from apps.reconcile.public import (
    cancel_reconcile_query,
    has_verified_reconcile_query_for_page_field,
    open_reconcile_query,
    reply_and_close_reconcile_query,
    reply_to_reconcile_query,
)
from apps.subject.application import (
    SubjectFormVerificationRequestValidator,
    SubjectValidationError,
)
from apps.subject.public import SubjectAbstractVerifyStudy

SELF_REVIEW_ERROR = "Bạn không được verify hoặc thao tác Query cho form do chính bạn cập nhật."


def _same_user(left, right) -> bool:
    try:
        return int(left) == int(right)
    except (TypeError, ValueError):
        return False


def _current_user_matches_submitted_entry_editor(*, request, subject_id: int, visit_id: int, crf_template_id: int) -> bool:
    submitted_entry = get_latest_submitted_page_entry_for_subject_visit_crf(
        subject_id=subject_id,
        visit_id=visit_id,
        crf_template_id=crf_template_id,
    )
    return _same_user(getattr(request.user, "id", None), getattr(submitted_entry, "updated_by_id", None))


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
            if _current_user_matches_submitted_entry_editor(
                request=request,
                subject_id=int(kwargs["subject_id"]),
                visit_id=int(kwargs["visit_id"]),
                crf_template_id=int(kwargs["crf_template_id"]),
            ):
                return JsonResponse({"error": [SELF_REVIEW_ERROR]}, status=400)
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


@method_decorator(csrf_exempt, name="dispatch")
class SubjectFormVerificationQueryThreadView(
    LoginRequiredMixin,
    SubjectAbstractVerifyStudy,
    View,
):

    def post(self, request, *args, **kwargs):
        try:
            normalized = SubjectFormVerificationRequestValidator.parse_query_thread_action(
                request.body
            )
            page_state_id = get_page_state_id_for_subject_visit_crf(
                subject_id=int(kwargs["subject_id"]),
                visit_id=int(kwargs["visit_id"]),
                crf_template_id=int(kwargs["crf_template_id"]),
            )
            if page_state_id is None:
                return JsonResponse({"error": ["Page state not found."]}, status=400)
            if normalized["cancel_query"]:
                result = cancel_reconcile_query(
                    dataquery_id=int(normalized["dataquery_id"]),
                    page_state_id=int(page_state_id),
                    field_template_id=int(normalized["field_template_id"]),
                    actor_user_id=getattr(request.user, "id", None),
                )
            elif normalized["close_query"]:
                result = reply_and_close_reconcile_query(
                    dataquery_id=int(normalized["dataquery_id"]),
                    page_state_id=int(page_state_id),
                    field_template_id=int(normalized["field_template_id"]),
                    message_text=str(normalized["message_text"]),
                    actor_user_id=getattr(request.user, "id", None),
                    is_resolved=normalized["is_resolved"],
                )
            else:
                result = reply_to_reconcile_query(
                    dataquery_id=int(normalized["dataquery_id"]),
                    page_state_id=int(page_state_id),
                    field_template_id=int(normalized["field_template_id"]),
                    message_text=str(normalized["message_text"]),
                    actor_user_id=getattr(request.user, "id", None),
                )
        except (SubjectValidationError, DataCaptureValidationError, ValueError) as exc:
            messages = list(exc.messages) if hasattr(exc, "messages") else [str(exc)]
            return JsonResponse({"error": messages}, status=400)
        return JsonResponse(
            {
                "ok": True,
                "dataquery_id": result["dataquery_id"],
                "message_text": result["message_text"],
                "message_type": result["message_type"],
                "created_at": result["created_at"],
                "closed": result["closed"],
                "cancelled": result.get("cancelled", False),
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class SubjectFormVerificationOpenQueryView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SubjectAbstractVerifyStudy,
    View,
):
    permission_required = "subject.verify_form"
    raise_exception = True

    def post(self, request, *args, **kwargs):
        try:
            normalized = SubjectFormVerificationRequestValidator.parse_open_query_action(
                request.body
            )
            page_state_id = get_page_state_id_for_subject_visit_crf(
                subject_id=int(kwargs["subject_id"]),
                visit_id=int(kwargs["visit_id"]),
                crf_template_id=int(kwargs["crf_template_id"]),
            )
            if page_state_id is None:
                return JsonResponse({"error": ["Page state not found."]}, status=400)
            page_state_status = get_page_state_status_for_subject_visit_crf(
                subject_id=int(kwargs["subject_id"]),
                visit_id=int(kwargs["visit_id"]),
                crf_template_id=int(kwargs["crf_template_id"]),
            )
            if (page_state_status or "").strip().lower() != DataCapturePageState.SUBMITTED:
                return JsonResponse({"error": ["Chỉ được tạo Query khi Page State ở trạng thái Submitted."]}, status=400)
            if _current_user_matches_submitted_entry_editor(
                request=request,
                subject_id=int(kwargs["subject_id"]),
                visit_id=int(kwargs["visit_id"]),
                crf_template_id=int(kwargs["crf_template_id"]),
            ):
                return JsonResponse({"error": [SELF_REVIEW_ERROR]}, status=400)
            if is_field_verified_for_page_state(
                page_state_id=int(page_state_id),
                field_template_id=int(normalized["field_template_id"]),
            ):
                return JsonResponse({"error": ["Dữ liệu đã được verify không thể tạo Query"]}, status=400)
            if has_verified_reconcile_query_for_page_field(
                page_state_id=int(page_state_id),
                field_template_id=int(normalized["field_template_id"]),
            ):
                return JsonResponse({"error": ["Query đã được verify không thể tạo Query mới"]}, status=400)
            result = open_reconcile_query(
                page_state_id=int(page_state_id),
                field_template_id=int(normalized["field_template_id"]),
                field_key=str(normalized.get("field_key") or ""),
                message_text=str(normalized["message_text"]),
                actor_user_id=getattr(request.user, "id", None),
            )
        except (SubjectValidationError, DataCaptureValidationError, ValueError) as exc:
            messages = list(exc.messages) if hasattr(exc, "messages") else [str(exc)]
            return JsonResponse({"error": messages}, status=400)
        return JsonResponse(
            {
                "ok": True,
                "dataquery_id": result["dataquery_id"],
                "field_template_id": result["field_template_id"],
                "message_text": result["message_text"],
                "message_type": result["message_type"],
                "created_at": result["created_at"],
            }
        )


__all__ = [
    "SubjectFormVerificationOpenQueryView",
    "SubjectFormVerificationQueryThreadView",
    "SubjectFormVerificationReopenView",
    "SubjectFormVerificationVerifyCheckedView",
]
