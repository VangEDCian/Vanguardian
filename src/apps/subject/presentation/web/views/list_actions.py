from types import SimpleNamespace

from django.http import Http404, HttpResponse
from django.template.loader import render_to_string
from django.views import View

from apps.shared.navigation import user_can_access_permission
from apps.shared.views import AuthenticateTemplateContextMixin
from apps.subject.application.services.early_termination import (
    SubjectEarlyTerminationAvailabilityService,
)
from apps.subject.application.services.subject_list_actions import (
    SubjectListActionsQueryService,
)
from apps.subject.application.services.subject_list_verify_form_visibility import (
    CRF_PAGE_LIFECYCLE_ACCESS_PERMISSIONS,
    SubjectListVerifyFormVisibilityService,
)
from apps.subject.application.services.workflow_action import (
    SubjectWorkflowActionService,
)
from apps.subject.presentation.web.views.base import SubjectAbstractVerifyStudy


class SubjectListActionsView(
    AuthenticateTemplateContextMixin,
    SubjectAbstractVerifyStudy,
    View,
):
    permission_required = "SUBJECT.VIEW"
    authorization_scope = "STUDY_SITE"
    require_site_context = True
    raise_exception = True
    verify_visibility_service_class = SubjectListVerifyFormVisibilityService
    workflow_action_service_class = SubjectWorkflowActionService
    early_termination_availability_service_class = (
        SubjectEarlyTerminationAvailabilityService
    )
    subject_query_service_class = SubjectListActionsQueryService

    def get(self, request, *args, **kwargs):
        subject = self.subject_query_service_class().get_subject(
            study_id=self.get_study_id(),
            subject_id=kwargs["subject_id"],
        )
        if subject is None:
            raise Http404

        permission_context = {
            "study_id": self.get_study_id(),
            "site_id": subject.site_id,
            "request": request,
        }
        can_verify_form = any(
            user_can_access_permission(
                request.user,
                permission_code,
                **permission_context,
            )
            for permission_code in CRF_PAGE_LIFECYCLE_ACCESS_PERMISSIONS
        )
        verify_map = self.verify_visibility_service_class().map_show_verify_form_by_subject_id(
            user_id=request.user.pk,
            has_verify_form_permission=can_verify_form,
            subject_ids=(subject.pk,),
        )
        can_update_subject = user_can_access_permission(
            request.user,
            "SUBJECT.UPDATE",
            **permission_context,
        )
        can_early_terminate = user_can_access_permission(
            request.user,
            "SUBJECT.EARLY_TERMINATE",
            **permission_context,
        )
        workflow_action_event_id_by_subject_id = {}
        workflow_access = (
            self.workflow_action_service_class()
            .map_triggerable_event_access_by_subject_id(
                study_id=self.get_study_id(),
                subject_ids=(subject.pk,),
            )
            .get(subject.pk)
        )
        if workflow_access and user_can_access_permission(
            request.user,
            workflow_access.permission_code,
            **permission_context,
        ):
            workflow_action_event_id_by_subject_id[subject.pk] = (
                workflow_access.event_instance_id
            )

        early_termination_eligible_subject_ids = frozenset()
        if can_early_terminate:
            early_termination_eligible_subject_ids = (
                self.early_termination_availability_service_class()
                .list_eligible_subject_ids(
                    study_id=self.get_study_id(),
                    subject_ids=(subject.pk,),
                )
            )
        table_context = SimpleNamespace(
            verify_eligible_subject_ids=frozenset(
                subject_id
                for subject_id, is_eligible in verify_map.items()
                if is_eligible
            ),
            workflow_action_event_id_by_subject_id=(
                workflow_action_event_id_by_subject_id
            ),
            can_update_subject=can_update_subject,
            can_early_terminate=can_early_terminate,
            early_termination_eligible_subject_ids=(
                early_termination_eligible_subject_ids
            ),
        )
        html = render_to_string(
            "subject/includes/subject_list_actions_cell.html",
            {
                "record": subject,
                "table": table_context,
            },
            request=request,
        )
        return HttpResponse(html)


__all__ = ["SubjectListActionsView"]
