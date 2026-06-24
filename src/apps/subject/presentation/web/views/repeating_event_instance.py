from django.contrib import messages
from django.core.exceptions import DisallowedHost
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views import View

from apps.shared.views import AuthenticateTemplateContextMixin
from apps.subject.application.services.add_repeating_event_instance import (
    AddRepeatingSubjectEventInstanceError,
    AddRepeatingSubjectEventInstanceService,
)
from apps.subject.presentation.web.views.base import SubjectAbstractVerifyStudy


class SubjectAddRepeatingEventInstanceView(
    AuthenticateTemplateContextMixin,
    SubjectAbstractVerifyStudy,
    View,
):
    permission_required = "subject.update_subject"
    authorization_scope = "STUDY_SITE"
    require_site_context = True
    raise_exception = True
    service_class = AddRepeatingSubjectEventInstanceService

    def post(self, request, *args, **kwargs):
        study_id = kwargs["study_id"]
        subject_id = kwargs["subject_id"]
        event_definition_id = kwargs["event_definition_id"]

        try:
            created_event = self.service_class().execute(
                study_id=study_id,
                subject_id=subject_id,
                event_definition_id=event_definition_id,
                actor_user_id=request.user.pk,
            )
        except AddRepeatingSubjectEventInstanceError as exc:
            messages.error(request, exc.message)
            return redirect(self._resolve_next_url(request, study_id=study_id, subject_id=subject_id))

        messages.success(
            request,
            _("Another %(event_name)s was created.") % {"event_name": created_event.event_name},
        )
        return redirect(
            f"{self._subject_detail_url(study_id=study_id, subject_id=subject_id)}?event={created_event.id}"
        )

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
        return self._subject_detail_url(study_id=study_id, subject_id=subject_id)

    @staticmethod
    def _subject_detail_url(*, study_id: int, subject_id: int) -> str:
        return reverse(
            "subject:subject_detail",
            kwargs={"study_id": study_id, "subject_id": subject_id},
        )


__all__ = ["SubjectAddRepeatingEventInstanceView"]
