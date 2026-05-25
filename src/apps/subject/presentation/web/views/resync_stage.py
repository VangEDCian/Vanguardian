import logging

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views import View

from apps.shared.views import AuthenticateTemplateContextMixin
from apps.subject.application.services.event_instance_resync import (
    SubjectEventInstanceResyncService,
)
from apps.subject.presentation.web.views.base import SubjectAbstractVerifyStudy

logger = logging.getLogger(__name__)


class SubjectResyncStageView(
    AuthenticateTemplateContextMixin,
    SubjectAbstractVerifyStudy,
    View,
):
    permission_required = "subject.update_subject"
    raise_exception = True
    service_class = SubjectEventInstanceResyncService

    def post(self, request, *args, **kwargs):
        study_id = kwargs["study_id"]
        subject_id = kwargs["subject_id"]
        next_url = self._resolve_next_url(request, study_id=study_id)

        try:
            result = self.service_class().resync_subject_active_study_version(
                study_id=study_id,
                subject_id=subject_id,
                actor_user_id=request.user.pk,
                trigger_source="subject_list_resync_stage",
            )
        except Exception:
            logger.exception(
                "Subject resync stage failed: study_id=%s subject_id=%s user_id=%s",
                study_id,
                subject_id,
                request.user.pk,
            )
            messages.error(request, _("Resync stage failed. Please check the server log for details."))
            return redirect(next_url)

        logger.info(
            "Subject resync stage result: study_id=%s subject_id=%s study_version=%s reason=%s subject_count=%s event_definition_count=%s created=%s updated=%s skipped_terminal=%s user_id=%s",
            study_id,
            subject_id,
            result.study_version,
            result.reason,
            result.subject_count,
            result.event_definition_count,
            result.created_count,
            result.updated_count,
            result.skipped_terminal_count,
            request.user.pk,
        )
        if not result.study_version or result.subject_count == 0:
            messages.warning(
                request,
                _("Resync stage did not run: %(reason)s.") % {"reason": result.reason or "unknown"},
            )
            return redirect(next_url)

        if not result.has_changes:
            messages.info(request, _("Subject stage is already up to date."))
            return redirect(next_url)

        messages.success(
            request,
            _(
                "Subject stage was resynced. Created: %(created_count)s, updated: %(updated_count)s, skipped: %(skipped_count)s."
            )
            % {
                "created_count": result.created_count,
                "updated_count": result.updated_count,
                "skipped_count": result.skipped_terminal_count,
            },
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


__all__ = ["SubjectResyncStageView"]
