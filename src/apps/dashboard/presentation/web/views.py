from django.utils.translation import gettext_lazy as _

from apps.dashboard.application import DashboardOverviewService
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
    dashboard_service_class = DashboardOverviewService

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        study_selection = StudyDropdownHandler(request=self.request).build()
        selected_study_id = study_selection.selected_id
        selected_site_id = self.get_filtered_site_id(study_id=selected_study_id)
        dashboard_context = self.get_dashboard_service().build(
            user=self.request.user,
            study_id=selected_study_id,
            site_id=selected_site_id,
        )
        context.update(dashboard_context)
        context["dashboard_selected_study_id"] = selected_study_id
        context["dashboard_selected_site_id"] = selected_site_id
        context["dashboard_selected_study_label"] = study_selection.select_display_text
        return context

    def get_dashboard_service(self):
        return self.dashboard_service_class()

    def get_filtered_site_id(self, *, study_id: int | None):
        raw_value = str(self.request.GET.get("site") or "").strip()
        if not raw_value or study_id is None:
            return None
        try:
            site_id = int(raw_value)
        except (TypeError, ValueError):
            return None
        exists = SiteDropdownHandler(request=self.request, study_id=study_id).get_objects().filter(pk=site_id).exists()
        return site_id if exists else None
