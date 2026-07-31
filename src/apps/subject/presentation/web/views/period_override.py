import logging

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views import View

from apps.shared.views import AuthenticateTemplateContextMixin
from apps.subject.application.services.period_override import (
    SubjectPeriodOverrideService,
)
from apps.subject.presentation.web.forms import SubjectPeriodOverrideForm
from apps.subject.presentation.web.views.base import SubjectAbstractVerifyStudy

logger = logging.getLogger(__name__)


class SubjectPeriodOverrideView(
    AuthenticateTemplateContextMixin,
    SubjectAbstractVerifyStudy,
    View,
):
    permission_required = "SUBJECT.PERIOD_OVERRIDE"
    authorization_scope = "STUDY_SITE"
    require_site_context = True
    raise_exception = True
    service_class = SubjectPeriodOverrideService

    def post(self, request, *args, **kwargs):
        study_id = kwargs["study_id"]
        subject_id = kwargs["subject_id"]
        next_url = self._resolve_next_url(
            request,
            study_id=study_id,
            subject_id=subject_id,
        )
        form = SubjectPeriodOverrideForm(request.POST)
        if not form.is_valid():
            messages.error(
                request,
                _("Period transition was not applied. Complete all required fields."),
            )
            return redirect(next_url)

        try:
            result = self.service_class().advance_to_next_period(
                study_id=study_id,
                subject_id=subject_id,
                actor_user_id=request.user.pk,
                period_end_at=form.cleaned_data["period_end_at"],
                next_period_start_at=form.cleaned_data["next_period_start_at"],
                reason_code=form.cleaned_data["reason_code"],
                reason_text=form.cleaned_data["reason_text"],
                pending_data_acknowledged=form.cleaned_data[
                    "pending_data_acknowledged"
                ],
                clinical_transition_confirmed=form.cleaned_data[
                    "clinical_transition_confirmed"
                ],
            )
        except Exception:
            logger.exception(
                "Subject period override failed: study_id=%s subject_id=%s user_id=%s",
                study_id,
                subject_id,
                request.user.pk,
            )
            messages.error(
                request,
                _("Period transition failed. Please check the server log for details."),
            )
            return redirect(next_url)

        if result.applied:
            messages.success(
                request,
                _("The next treatment period is now active. Existing CRF statuses were not changed."),
            )
            return redirect(next_url)

        messages.warning(
            request,
            _("Period transition was not applied: %(reason)s.")
            % {"reason": result.reason or "unknown"},
        )
        return redirect(next_url)

    @staticmethod
    def _resolve_next_url(
        request,
        *,
        study_id: int,
        subject_id: int,
    ) -> str:
        next_url = (request.POST.get("next") or "").strip()
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return next_url
        return reverse(
            "subject:subject_detail",
            kwargs={"study_id": study_id, "subject_id": subject_id},
        )


__all__ = ["SubjectPeriodOverrideView"]
