from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse

from apps.shared.context_processors import SiteDropdownHandler
from apps.shared.views import AuthenticateTemplateContextMixin
from apps.subject.application.services import CreateSubjectService
from apps.subject.presentation.web.mappers.create_subject import to_create_subject_command
from apps.subject.presentation.web.views.base import SubjectAbstractVerifyStudy


class SubjectCreateView(
    AuthenticateTemplateContextMixin,
    SubjectAbstractVerifyStudy,
):
    permission_required = "subject.create_subject"
    authorization_scope = "STUDY_SITE"
    require_site_context = True
    raise_exception = True

    def post(self, request, *args, **kwargs):
        study_id = self.get_study_id()
        site_id = SiteDropdownHandler(
            request=request,
            study_id=study_id,
        ).build().selected_id
        if site_id is None:
            raise Http404

        subject = CreateSubjectService().execute(
            to_create_subject_command(
                study_id=study_id,
                site_id=site_id,
                actor_user_id=request.user.pk,
            ),
        )
        return redirect(
            reverse(
                "subject:subject_detail",
                kwargs={"study_id": study_id, "subject_id": subject.pk},
            ),
        )
