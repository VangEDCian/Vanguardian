import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.utils.translation import get_language
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.datacapture.application.exceptions import DataCaptureValidationError
from apps.datacapture.application.services.event_attestation import DataCaptureEventAttestationService
from apps.identity.presentation.mixins import ContextPermissionRequiredMixin
from apps.subject.public import SubjectAbstractVerifyStudy


def _json_body(request) -> dict:
    try:
        loaded = json.loads(request.body.decode("utf-8") or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


@method_decorator(csrf_exempt, name="dispatch")
class DataCaptureEventAttestationSubmitAPIView(
    LoginRequiredMixin,
    ContextPermissionRequiredMixin,
    SubjectAbstractVerifyStudy,
    View,
):
    permission_required = "EVENT_CERTIFICATION.CERTIFY"
    authorization_scope = "STUDY_SITE"
    require_site_context = True
    raise_exception = True

    def post(self, request, *args, **kwargs):
        payload = _json_body(request)
        try:
            result = DataCaptureEventAttestationService().attest_event_for_policy(
                event_instance_id=int(kwargs["visit_id"]),
                attestation_policy_id=int(kwargs["attestation_policy_id"]),
                actor_user_id=int(request.user.pk),
                actor_is_superuser=bool(getattr(request.user, "is_superuser", False)),
                language_code=get_language(),
                confirmation_accepted=bool(payload.get("confirmation_accepted")),
                expected_study_id=int(kwargs["study_id"]),
                expected_subject_id=int(kwargs["subject_id"]),
            )
        except (DataCaptureValidationError, ValueError) as exc:
            messages = list(exc.messages) if hasattr(exc, "messages") else [str(exc)]
            return JsonResponse({"error": messages}, status=400)
        return JsonResponse({**result, "reload_required": True})


@method_decorator(csrf_exempt, name="dispatch")
class DataCaptureEventAttestationRevokeAPIView(
    LoginRequiredMixin,
    ContextPermissionRequiredMixin,
    SubjectAbstractVerifyStudy,
    View,
):
    permission_required = "EVENT_ATTESTATION.REVOKE"
    authorization_scope = "STUDY_SITE"
    require_site_context = True
    raise_exception = True

    def post(self, request, *args, **kwargs):
        payload = _json_body(request)
        try:
            result = DataCaptureEventAttestationService().revoke_event_attestation(
                event_attestation_id=int(kwargs["event_attestation_id"]),
                actor_user_id=int(request.user.pk),
                actor_is_superuser=bool(getattr(request.user, "is_superuser", False)),
                reason_text=str(payload.get("reason_text") or ""),
                expected_study_id=int(kwargs["study_id"]),
                expected_subject_id=int(kwargs["subject_id"]),
            )
        except (DataCaptureValidationError, ValueError) as exc:
            messages = list(exc.messages) if hasattr(exc, "messages") else [str(exc)]
            return JsonResponse({"error": messages}, status=400)
        return JsonResponse({**result, "reload_required": True})


__all__ = [
    "DataCaptureEventAttestationRevokeAPIView",
    "DataCaptureEventAttestationSubmitAPIView",
]
