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
from apps.study.public import (
    build_randomization_transition_facts,
    get_subject_identifier_policy,
    list_subject_export_field_groups,
)
from apps.subject.application.services.early_termination import (
    SubjectEarlyTerminationAvailabilityService,
)
from apps.subject.application.services.subject_list_verify_form_visibility import (
    VERIFY_FORM_PERMISSION,
    SubjectListVerifyFormVisibilityService,
)
from apps.subject.application.services.treatment_timeline import SubjectTreatmentTimelineService
from apps.subject.application.services.workflow_action import SubjectWorkflowActionService
from apps.subject.presentation.web.forms import SubjectsToolbarForm
from apps.subject.presentation.web.mappers.subject_list_model import get_subject_list_row_model
from apps.subject.presentation.web.tables import SubjectListTable
from apps.subject.presentation.web.views.base import (
    CRF_DATA_CHANGE_PERMISSIONS,
    SubjectAbstractVerifyStudy,
)


class SubjectListView(
    AuthenticateTemplateContextMixin,
    SingleTableMixin,
    FilterView,
    ListView,
    SubjectAbstractVerifyStudy,
):
    permission_required = "SUBJECT.VIEW"
    raise_exception = True
    layout_nav_key = "SUBJECTS"
    layout_breadcrumb_label = _("SUBJECTS")

    model = get_subject_list_row_model()
    template_name = "subject/subjects.html"
    table_class = SubjectListTable
    filterset_class = SubjectsToolbarForm
    paginate_by = 25
    workflow_action_service_class = SubjectWorkflowActionService
    treatment_timeline_service_class = SubjectTreatmentTimelineService
    early_termination_availability_service_class = (
        SubjectEarlyTerminationAvailabilityService
    )
    randomization_transition_fact_builder = staticmethod(
        build_randomization_transition_facts
    )

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
            .select_related("site", "study", "enrollment", "randomization", "randomization__slot")
            .order_by("current_sequence", "id")
        )

    def get_table(self, **kwargs):
        # OLD: return RequestConfig(...).configure(table_class(data=self.get_table_data(), **kwargs))
        table_class = self.get_table_class()
        table_data = self.get_table_data()
        subject_site_by_id = dict(table_data.values_list("pk", "site_id"))
        subject_ids = tuple(subject_site_by_id)
        visibility = SubjectListVerifyFormVisibilityService()
        can_verify_form = user_can_access_permission(
            self.request.user,
            VERIFY_FORM_PERMISSION,
            study_id=self.get_study_id(),
            site_id=self.get_selected_site_id(),
            request=self.request,
        )
        can_update_subject = user_can_access_permission(
            self.request.user,
            "SUBJECT.UPDATE",
            study_id=self.get_study_id(),
            site_id=self.get_selected_site_id(),
            request=self.request,
        )
        can_early_terminate = user_can_access_permission(
            self.request.user,
            "SUBJECT.EARLY_TERMINATE",
            study_id=self.get_study_id(),
            site_id=self.get_selected_site_id(),
            request=self.request,
        )
        verify_map = visibility.map_show_verify_form_by_subject_id(
            user_id=self.request.user.pk,
            has_verify_form_permission=can_verify_form,
            subject_ids=subject_ids,
        )
        current_treatment_map = (
            self.treatment_timeline_service_class().map_current_subject_treatment_by_subject_id(
                subject_ids=subject_ids,
            )
        )
        workflow_service = self.workflow_action_service_class()
        workflow_action_access_map = (
            workflow_service.map_triggerable_event_access_by_subject_id(
                study_id=self.get_study_id(),
                subject_ids=subject_ids,
            )
        )
        workflow_permission_by_scope = {}
        workflow_action_event_map = {}
        for subject_id, access in workflow_action_access_map.items():
            permission_scope = (
                access.permission_code,
                subject_site_by_id.get(subject_id),
            )
            if permission_scope not in workflow_permission_by_scope:
                workflow_permission_by_scope[permission_scope] = (
                    user_can_access_permission(
                        self.request.user,
                        access.permission_code,
                        study_id=self.get_study_id(),
                        site_id=subject_site_by_id.get(subject_id),
                        request=self.request,
                    )
                )
            if workflow_permission_by_scope[permission_scope]:
                workflow_action_event_map[subject_id] = access.event_instance_id
        early_termination_eligible_subject_ids = frozenset()
        if can_early_terminate:
            early_termination_eligible_subject_ids = (
                self.early_termination_availability_service_class()
                .list_eligible_subject_ids(
                    study_id=self.get_study_id(),
                    subject_ids=subject_ids,
                )
            )
        detail_url_by_subject_id = self._build_detail_url_by_subject_id(
            subject_site_by_id=subject_site_by_id,
        )
        table = table_class(
            table_data,
            verify_show_by_subject_id=verify_map,
            current_treatment_by_subject_id=current_treatment_map,
            workflow_action_event_id_by_subject_id=workflow_action_event_map,
            detail_url_by_subject_id=detail_url_by_subject_id,
            can_update_subject=can_update_subject,
            can_early_terminate=can_early_terminate,
            early_termination_eligible_subject_ids=(
                early_termination_eligible_subject_ids
            ),
            randomization_transition_facts=(
                self.randomization_transition_fact_builder(
                    study_id=self.get_study_id(),
                )
            ),
            **kwargs,
        )
        return RequestConfig(self.request, paginate=self.get_table_pagination(table)).configure(table)

    def _build_detail_url_by_subject_id(
        self,
        *,
        subject_site_by_id: dict[int, int],
    ) -> dict[int, str]:
        permissions_by_site_id = {}
        for site_id in set(subject_site_by_id.values()):
            permissions_by_site_id[site_id] = {
                "can_change_crf_data": any(
                    user_can_access_permission(
                        self.request.user,
                        permission_code,
                        study_id=self.get_study_id(),
                        site_id=site_id,
                        request=self.request,
                    )
                    for permission_code in CRF_DATA_CHANGE_PERMISSIONS
                ),
                "can_verify_form": user_can_access_permission(
                    self.request.user,
                    VERIFY_FORM_PERMISSION,
                    study_id=self.get_study_id(),
                    site_id=site_id,
                    request=self.request,
                ),
                "can_view_subject": user_can_access_permission(
                    self.request.user,
                    self.permission_required,
                    study_id=self.get_study_id(),
                    site_id=site_id,
                    request=self.request,
                ),
            }

        return {
            subject_id: self._resolve_detail_url(
                study_id=self.get_study_id(),
                subject_id=subject_id,
                **permissions_by_site_id[site_id],
            )
            for subject_id, site_id in subject_site_by_id.items()
        }

    @staticmethod
    def _resolve_detail_url(
        *,
        study_id: int,
        subject_id: int,
        can_change_crf_data: bool,
        can_verify_form: bool,
        can_view_subject: bool,
    ) -> str:
        base_url = reverse(
            "subject:subject_detail",
            kwargs={"study_id": study_id, "subject_id": subject_id},
        )
        if can_change_crf_data:
            return base_url
        if can_verify_form:
            return f"{base_url}?mode=verification"
        if can_view_subject:
            return f"{base_url}?mode=viewonly"
        return ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        permission_context = {
            "study_id": self.get_study_id(),
            "site_id": self.get_selected_site_id(),
            "request": self.request,
        }
        context["can_create_subject"] = user_can_access_permission(
            self.request.user, "SUBJECT.CREATE", **permission_context
        )
        context["can_delete_subject"] = user_can_access_permission(
            self.request.user, "subject.delete_subject", **permission_context
        )
        context["can_bulk_resync_subject"] = user_can_access_permission(
            self.request.user, "SUBJECT.UPDATE", **permission_context
        )
        context["can_bulk_early_terminate_subject"] = user_can_access_permission(
            self.request.user, "SUBJECT.EARLY_TERMINATE", **permission_context
        )
        context["can_export_subjects"] = user_can_access_permission(
            self.request.user,
            "DATA_EXPORT.RUN",
            **permission_context,
        )
        context["subject_export_field_groups"] = (
            list_subject_export_field_groups(study_id=self.get_study_id())
            if context["can_export_subjects"]
            else []
        )
        context["subject_filtered_count"] = context["filter"].qs.count()
        context["subject_identifier_policy"] = get_subject_identifier_policy(
            study_id=self.get_study_id()
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
