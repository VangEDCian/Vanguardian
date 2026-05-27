from django.db.models import Count, Q
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from django_filters.views import FilterView
from django_tables2 import SingleTableMixin
from django_tables2.views import RequestConfig

from apps.reconcile.models import ReconcileDataQueryStatusChoices, ReconcileValidationIssueStatusChoices
from apps.shared.context_processors import SiteDropdownHandler, StudyDropdownHandler
from apps.shared.navigation import get_default_authenticated_url, user_can_access_permission
from apps.shared.views import AuthenticateTemplateContextMixin
from apps.subject.application.services.subject_list_verify_form_visibility import (
    VERIFY_FORM_PERMISSION,
    SubjectListVerifyFormVisibilityService,
)
from apps.subject.application.services.workflow_action import SubjectWorkflowActionService
from apps.subject.presentation.web.forms import SubjectsToolbarForm
from apps.subject.presentation.web.mappers.subject_list_model import get_subject_list_row_model
from apps.subject.presentation.web.tables import SubjectListTable
from apps.subject.presentation.web.views.base import SubjectAbstractVerifyStudy


class SubjectListView(
    AuthenticateTemplateContextMixin,
    SingleTableMixin,
    FilterView,
    ListView,
    SubjectAbstractVerifyStudy,
):
    permission_required = "subject.view_subject_list"
    raise_exception = True
    layout_nav_key = "SUBJECTS"
    layout_breadcrumb_label = _("SUBJECTS")

    model = get_subject_list_row_model()
    template_name = "subject/subjects.html"
    table_class = SubjectListTable
    filterset_class = SubjectsToolbarForm
    paginate_by = 25
    workflow_action_service_class = SubjectWorkflowActionService

    @staticmethod
    def _get_resolved_study_id(request):
        return StudyDropdownHandler(request=request).build().selected_id

    def get_selected_site_id(self):
        return SiteDropdownHandler(
            request=self.request,
            study_id=self.get_study_id(),
        ).build().selected_id

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(study_id=self.get_study_id(), deleted=False)
            .annotate(
                open_query_count=Count(
                    "data_capture_page_states__reconcile_data_queries",
                    filter=Q(
                        data_capture_page_states__deleted=False,
                        data_capture_page_states__reconcile_data_queries__deleted=False,
                        data_capture_page_states__reconcile_data_queries__status=ReconcileDataQueryStatusChoices.OPEN,
                    ),
                    distinct=True,
                ),
                validation_issue_count=Count(
                    "data_capture_page_states__reconcile_validation_issues",
                    filter=Q(
                        data_capture_page_states__deleted=False,
                        data_capture_page_states__reconcile_validation_issues__status__in=(
                            ReconcileValidationIssueStatusChoices.OPEN,
                            ReconcileValidationIssueStatusChoices.ACKNOWLEDGEMENT_REQUIRED,
                        ),
                    ),
                    distinct=True,
                ),
            )
            .select_related("site", "study", "enrollment", "randomization")
            .order_by("current_sequence", "id")
        )

    def get_table(self, **kwargs):
        # OLD: return RequestConfig(...).configure(table_class(data=self.get_table_data(), **kwargs))
        table_class = self.get_table_class()
        table_data = self.get_table_data()
        subject_ids = tuple(table_data.values_list("pk", flat=True))
        visibility = SubjectListVerifyFormVisibilityService()
        can_verify_form = user_can_access_permission(
            self.request.user,
            VERIFY_FORM_PERMISSION,
            study_id=self.get_study_id(),
            site_id=self.get_selected_site_id(),
        )
        can_update_subject = user_can_access_permission(
            self.request.user,
            "subject.update_subject",
            study_id=self.get_study_id(),
            site_id=self.get_selected_site_id(),
        )
        verify_map = visibility.map_show_verify_form_by_subject_id(
            user_id=self.request.user.pk,
            has_verify_form_permission=can_verify_form,
            subject_ids=subject_ids,
        )
        workflow_action_event_map = {}
        if can_update_subject:
            workflow_service = self.workflow_action_service_class()
            workflow_action_event_map = workflow_service.map_triggerable_event_instance_id_by_subject_id(
                study_id=self.get_study_id(),
                subject_ids=subject_ids,
            )
        table = table_class(
            table_data,
            verify_show_by_subject_id=verify_map,
            workflow_action_event_id_by_subject_id=workflow_action_event_map,
            can_update_subject=can_update_subject,
            **kwargs,
        )
        return RequestConfig(self.request, paginate=self.get_table_pagination(table)).configure(table)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_create_subject"] = user_can_access_permission(
            self.request.user,
            "subject.create_subject",
            study_id=self.get_study_id(),
            site_id=self.get_selected_site_id(),
        )
        return context

    def get(self, request, *args, **kwargs):
        path_study_id = self.get_study_id()
        resolved_study_id = self._get_resolved_study_id(request)
        if path_study_id and resolved_study_id:
            if path_study_id == resolved_study_id:
                return super().get(request, *args, **kwargs)
            return redirect(
                reverse(
                    "subject:subject_list",
                    kwargs={"study_id": resolved_study_id},
                )
            )
        return redirect(get_default_authenticated_url(request))
