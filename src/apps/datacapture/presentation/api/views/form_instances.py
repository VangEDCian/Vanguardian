from django.http import JsonResponse
from django.utils.translation import get_language
from django.views import View

from apps.audit.public import build_audit_request_context
from apps.datacapture.application.services.form_instances import (
    DataCaptureFormInstanceService,
)
from apps.identity.presentation.mixins import ContextPermissionRequiredMixin
from apps.subject.public import SubjectAbstractVerifyStudy


class DataCaptureFormInstanceListCreateAPIView(
    ContextPermissionRequiredMixin,
    SubjectAbstractVerifyStudy,
    View,
):
    permission_required = "subject.view_subject_detail"
    authorization_scope = "STUDY_SITE"
    require_site_context = True
    raise_exception = True
    service_class = DataCaptureFormInstanceService

    def get_service(self):
        return self.service_class()

    def dispatch(self, request, *args, **kwargs):
        # The same URL lists existing instances with read permission and creates
        # a new repeated capture instance with CRF entry permission.
        if request.method.upper() == "POST":
            self.permission_required = "CRF.ENTER"
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        payload = self.get_service().list_form_instances_for_event_instance(
            visit_id=kwargs["visit_id"],
            language_code=get_language(),
        )
        return JsonResponse(
            {
                "results": [
                    {
                        "page_state_id": row.page_state_id,
                        "instance_key": row.instance_key,
                        "repeat_index": row.repeat_index,
                        "event_form_binding_id": row.event_form_binding_id,
                        "crf_template_id": row.crf_template_id,
                        "template_name": row.template_name,
                        "display_label": row.display_label,
                        "status": row.status,
                    }
                    for row in payload
                ]
            }
        )

    def post(self, request, *args, **kwargs):
        event_form_binding_id = int(
            request.POST.get("event_form_binding_id") or request.GET.get("event_form_binding_id")
        )
        dto = self.get_service().create_form_instance(
            subject_id=kwargs["subject_id"],
            visit_id=kwargs["visit_id"],
            event_form_binding_id=event_form_binding_id,
            actor_user_id=request.user.pk,
            **build_audit_request_context(request),
        )
        return JsonResponse(
            {
                "page_state_id": dto.page_state_id,
                "instance_key": dto.instance_key,
                "repeat_index": dto.repeat_index,
                "event_form_binding_id": dto.event_form_binding_id,
                "crf_template_id": dto.crf_template_id,
                "template_name": dto.template_name,
                "display_label": dto.display_label,
                "status": dto.status,
            },
            status=201,
        )
