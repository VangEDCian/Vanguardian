from django.utils.translation import gettext_lazy as _

from apps.shared.views.generic import AuthenticateTemplateView


class DashboardMainView(AuthenticateTemplateView):
    permission_required = "dashboard.view_dashboard"
    require_study_context = False
    allow_global_permission_check = True
    raise_exception = True
    template_name = "dashboard/main.html"
    layout_nav_key = "DASHBOARD"
    layout_breadcrumb_label = _("DASHBOARD")
