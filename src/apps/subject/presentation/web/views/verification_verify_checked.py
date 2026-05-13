import json

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.datacapture.public import merge_form_verification_checked_fields_into_page_state_final_data
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
            body = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": ["Invalid JSON"]}, status=400)
        raw_ids = body.get("field_template_ids")
        if raw_ids is None:
            raw_ids = []
        if not isinstance(raw_ids, list):
            return JsonResponse({"error": ["field_template_ids must be a list"]}, status=400)
        normalized: list[int] = []
        for item in raw_ids:
            try:
                normalized.append(int(item))
            except (TypeError, ValueError):
                return JsonResponse({"error": ["field_template_ids must contain integers"]}, status=400)
        try:
            all_verified, page_status = merge_form_verification_checked_fields_into_page_state_final_data(
                subject_id=int(kwargs["subject_id"]),
                visit_id=int(kwargs["visit_id"]),
                crf_template_id=int(kwargs["crf_template_id"]),
                checked_field_template_ids=normalized,
                actor_user_id=getattr(request.user, "id", None),
            )
        except ValidationError as exc:
            return JsonResponse({"error": list(exc.messages)}, status=400)
        return JsonResponse(
            {
                "ok": True,
                "field_template_ids": normalized,
                "all_verified": all_verified,
                "page_status": page_status,
            }
        )


__all__ = ["SubjectFormVerificationVerifyCheckedView"]
