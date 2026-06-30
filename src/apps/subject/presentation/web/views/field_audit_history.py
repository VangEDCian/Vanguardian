from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, JsonResponse
from django.views import View

from apps.identity.presentation.mixins import ContextPermissionRequiredMixin
from apps.subject.application.services.field_audit_history import SubjectFieldAuditHistoryQueryService
from apps.subject.presentation.web.views.base import SubjectAbstractVerifyStudy


class SubjectFieldAuditHistoryView(
    LoginRequiredMixin,
    ContextPermissionRequiredMixin,
    SubjectAbstractVerifyStudy,
    View,
):
    permission_required = "subject.view_subject_detail"
    authorization_scope = "STUDY_SITE"
    require_site_context = True
    raise_exception = True
    service_class = SubjectFieldAuditHistoryQueryService

    def get_service(self):
        return self.service_class()

    def get(self, request, *args, **kwargs):
        try:
            field_template_id = int(request.GET.get("field_template_id") or request.GET.get("fieldTemplateId") or 0)
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "error": ["Invalid field template."]}, status=400)
        if field_template_id <= 0:
            return JsonResponse({"ok": False, "error": ["Invalid field template."]}, status=400)

        field_key = str(request.GET.get("field_key") or request.GET.get("fieldKey") or "").strip()
        event_form_binding_id = self._event_form_binding_id_from_request(request)
        history = self.get_service().get_field_audit_history(
            study_id=self.get_study_id(),
            subject_id=self.kwargs["subject_id"],
            visit_id=self.kwargs["visit_id"],
            crf_template_id=self.kwargs["crf_template_id"],
            field_template_id=field_template_id,
            field_key=field_key,
            event_form_binding_id=event_form_binding_id,
        )
        if history is None:
            raise Http404
        return JsonResponse({"ok": True, "history": history})

    @staticmethod
    def _event_form_binding_id_from_request(request):
        raw_value = request.GET.get("form") or request.GET.get("event_form_binding_id") or ""
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return None


__all__ = ["SubjectFieldAuditHistoryView"]
