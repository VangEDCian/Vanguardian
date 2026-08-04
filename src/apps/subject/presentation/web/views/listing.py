from django.db.models import Count, Q
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
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
)
from apps.subject.application.services.subject_list_verify_form_visibility import (
    CRF_PAGE_LIFECYCLE_ACCESS_PERMISSIONS,
)
from apps.subject.application.services.treatment_timeline import SubjectTreatmentTimelineService
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
    paginate_by = None
    table_pagination = {"per_page": 25}
    treatment_timeline_service_class = SubjectTreatmentTimelineService
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
            .select_related("enrollment", "randomization")
            .only(
                "id",
                "created_at",
                "subject_code",
                "screening_code",
                "current_sequence",
                "lifecycle_status",
                "study_id",
                "site_id",
                "enrollment__id",
                "enrollment__subject_id",
                "enrollment__deleted",
                "enrollment__status",
                "enrollment__is_enrolled",
                "enrollment__enrollment_date",
                "randomization__id",
                "randomization__subject_id",
                "randomization__deleted",
                "randomization__created_at",
                "randomization__randomization_status",
                "randomization__randomization_number",
                "randomization__slot_id",
            )
            .order_by("current_sequence", "id")
        )

    def get_table(self, **kwargs):
        table_class = self.get_table_class()
        table_data = self.get_table_data()
        table = table_class(
            table_data,
            randomization_transition_facts=(
                self.randomization_transition_fact_builder(
                    study_id=self.get_study_id(),
                )
            ),
            **kwargs,
        )
        table.assets_bundled = True
        table = RequestConfig(
            self.request,
            paginate=self.get_table_pagination(table),
        ).configure(table)
        subject_site_by_id = {
            row.record.pk: row.record.site_id
            for row in table.paginated_rows
        }
        subject_ids = tuple(subject_site_by_id)
        current_treatment_map = (
            self.treatment_timeline_service_class().map_current_subject_treatment_by_subject_id(
                subject_ids=subject_ids,
            )
        )
        detail_url_by_subject_id = self._build_detail_url_by_subject_id(
            subject_site_by_id=subject_site_by_id,
        )
        table.bind_runtime_context(
            current_treatment_by_subject_id=current_treatment_map,
            detail_url_by_subject_id=detail_url_by_subject_id,
        )
        return table

    def get_filterset_kwargs(self, filterset_class):
        kwargs = super().get_filterset_kwargs(filterset_class)
        kwargs["defer_total_count"] = True
        return kwargs

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
                "can_verify_form": any(
                    user_can_access_permission(
                        self.request.user,
                        permission_code,
                        study_id=self.get_study_id(),
                        site_id=site_id,
                        request=self.request,
                    )
                    for permission_code in CRF_PAGE_LIFECYCLE_ACCESS_PERMISSIONS
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
        table = context["table"]
        filtered_count = table.paginator.count
        context["filter"].bind_total_field(total_value=filtered_count)
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
        context["subject_filtered_count"] = filtered_count
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
