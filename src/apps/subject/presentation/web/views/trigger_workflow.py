import logging

from django.contrib import messages
from django.core.exceptions import DisallowedHost
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views import View

from apps.shared.views import AuthenticateTemplateContextMixin
from apps.subject.application.services.workflow_action import SubjectWorkflowActionService
from apps.subject.presentation.web.views.base import SubjectAbstractVerifyStudy

logger = logging.getLogger(__name__)


class SubjectTriggerWorkflowView(
    AuthenticateTemplateContextMixin,
    SubjectAbstractVerifyStudy,
    View,
):
    permission_required = "subject.update_subject"
    authorization_scope = "STUDY_SITE"
    require_site_context = True
    raise_exception = True
    service_class = SubjectWorkflowActionService

    def post(self, request, *args, **kwargs):
        study_id = kwargs["study_id"]
        subject_id = kwargs["subject_id"]
        event_instance_id = kwargs["event_instance_id"]
        next_url = self._resolve_next_url(request, study_id=study_id, subject_id=subject_id)
        service = self.service_class()

        if not service.can_trigger_event_instance(
            study_id=study_id,
            subject_id=subject_id,
            event_instance_id=event_instance_id,
        ):
            messages.warning(request, _("Workflow cannot be triggered for this event."))
            return redirect(next_url)

        try:
            result = service.execute_for_open_event(
                event_instance_id=event_instance_id,
                actor_user_id=request.user.pk,
            )
        except Exception:
            logger.exception(
                "Subject trigger workflow failed: study_id=%s subject_id=%s event_instance_id=%s user_id=%s",
                study_id,
                subject_id,
                event_instance_id,
                request.user.pk,
            )
            messages.error(request, _("Trigger workflow failed. Please check the server log for details."))
            return redirect(next_url)

        logger.info(
            "Subject trigger workflow result: study_id=%s subject_id=%s event_instance_id=%s "
            "executed=%s action=%s reason=%s user_id=%s",
            study_id,
            subject_id,
            event_instance_id,
            result.executed,
            result.action,
            result.reason,
            request.user.pk,
        )
        if result.executed:
            messages.success(
                request,
                _("Workflow was triggered: %(action)s.") % {"action": result.action or "workflow"},
            )
            return redirect(next_url)

        messages.warning(
            request,
            _("Workflow did not run: %(reason)s.") % {"reason": result.reason or "unknown"},
        )
        return redirect(next_url)

    def _resolve_next_url(self, request, *, study_id: int, subject_id: int) -> str:
        next_url = (request.POST.get("next") or "").strip()
        if next_url:
            try:
                current_host = request.get_host()
            except DisallowedHost:
                current_host = ""
            if current_host and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={current_host},
                require_https=request.is_secure(),
            ):
                return next_url
        return reverse(
            "subject:subject_detail",
            kwargs={"study_id": study_id, "subject_id": subject_id},
        )


__all__ = ["SubjectTriggerWorkflowView"]
