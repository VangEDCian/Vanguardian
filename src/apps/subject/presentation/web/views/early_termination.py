import logging

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views import View

from apps.shared.views import AuthenticateTemplateContextMixin
from apps.subject.application.services.early_termination import (
    SubjectEarlyTerminationRequestService,
)
from apps.subject.presentation.web.views.base import SubjectAbstractVerifyStudy

logger = logging.getLogger(__name__)


class SubjectEarlyTerminationRequestView(
    AuthenticateTemplateContextMixin,
    SubjectAbstractVerifyStudy,
    View,
):
    permission_required = "subject.update_subject"
    authorization_scope = "STUDY_SITE"
    require_site_context = True
    raise_exception = True
    service_class = SubjectEarlyTerminationRequestService

    def post(self, request, *args, **kwargs):
        study_id = kwargs["study_id"]
        subject_id = kwargs["subject_id"]
        next_url = self._resolve_next_url(request, study_id=study_id)

        try:
            result = self.service_class().request(
                study_id=study_id,
                subject_id=subject_id,
                actor_user_id=request.user.pk,
            )
        except Exception:
            logger.exception(
                "Subject early termination request failed: study_id=%s subject_id=%s user_id=%s",
                study_id,
                subject_id,
                request.user.pk,
            )
            messages.error(request, _("Early termination request failed. Please check the server log for details."))
            return redirect(next_url)

        logger.info(
            "Subject early termination request result: study_id=%s subject_id=%s "
            "requested=%s source_event_instance_id=%s opened_event_instance_ids=%s reason=%s user_id=%s",
            study_id,
            subject_id,
            result.requested,
            result.source_event_instance_id,
            result.opened_event_instance_ids,
            result.reason,
            request.user.pk,
        )
        if result.requested:
            messages.success(request, _("Early termination visit was opened."))
            return redirect(next_url)

        messages.warning(
            request,
            _("Early termination visit was not opened: %(reason)s.") % {"reason": result.reason or "unknown"},
        )
        return redirect(next_url)

    def _resolve_next_url(self, request, *, study_id: int) -> str:
        next_url = (request.POST.get("next") or "").strip()
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return next_url
        return reverse("subject:subject_list", kwargs={"study_id": study_id})


__all__ = ["SubjectEarlyTerminationRequestView"]
