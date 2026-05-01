from django.utils.translation import gettext_lazy as _

from apps.shared.views.generic import AuthenticateTemplateView


class DashboardMainView(AuthenticateTemplateView):
    template_name = "dashboard/main.html"
    layout_nav_key = "DASHBOARD"
    layout_breadcrumb_label = _("DASHBOARD")
