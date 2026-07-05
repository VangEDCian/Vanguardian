from django.utils.translation import gettext_lazy as _

from apps.reconcile.application.services.query_workbench import QueryWorkbenchReader, QueryWorkbenchSummaryDTO
from apps.shared.context_processors import SiteDropdownHandler, StudyDropdownHandler
from apps.shared.views.generic import AuthenticateTemplateView


class DashboardMainView(AuthenticateTemplateView):
    permission_required = "dashboard.view_dashboard"
    require_study_context = False
    allow_global_permission_check = True
    raise_exception = True
    template_name = "dashboard/main.html"
    layout_nav_key = "DASHBOARD"
    layout_breadcrumb_label = _("DASHBOARD")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_study_id = StudyDropdownHandler(request=self.request).build().selected_id
        selected_site_id = SiteDropdownHandler(
            request=self.request,
            study_id=selected_study_id,
        ).build().selected_id
        summary = self._read_query_summary(
            study_id=selected_study_id,
            site_id=selected_site_id,
        )
        context["query_summary_rows"] = (
            {
                "label": _("Open"),
                "count": summary.open,
                "icon_class": "dashboard-query-summary__icon--rose",
            },
            {
                "label": _("Waiting CRA Review"),
                "count": summary.awaiting_review,
                "icon_class": "dashboard-query-summary__icon--amber",
            },
            {
                "label": _("Blocking"),
                "count": summary.blocking_open,
                "icon_class": "dashboard-query-summary__icon--slate",
            },
            {
                "label": _("Resolved"),
                "count": summary.resolved,
                "icon_class": "dashboard-query-summary__icon--outline",
            },
            {
                "label": _("Closed"),
                "count": summary.closed,
                "icon_class": "dashboard-query-summary__icon--slate",
            },
        )
        context["query_summary_total"] = summary.total
        context["dashboard_selected_study_id"] = selected_study_id
        context["dashboard_selected_site_id"] = selected_site_id
        return context

    def get_query_workbench_reader(self):
        return QueryWorkbenchReader()

    def _read_query_summary(self, *, study_id: int | None, site_id: int | None):
        if study_id is None:
            return self._empty_query_summary()
        return self.get_query_workbench_reader().read(
            study_id=study_id,
            site_id=site_id,
            current_user_id=getattr(self.request.user, "pk", None),
            can_view_internal_thread=False,
        ).summary

    @staticmethod
    def _empty_query_summary():
        return QueryWorkbenchSummaryDTO(
            total=0,
            open=0,
            awaiting_site_response=0,
            awaiting_review=0,
            blocking_open=0,
            resolved=0,
            closed=0,
            validation_issues_open=0,
            hard_validation_issues_open=0,
            actionable_for_current_user=0,
        )
