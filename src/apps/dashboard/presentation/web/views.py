from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _

from apps.shared.views.generic import AuthenticateTemplateView


class DashboardMainView(LoginRequiredMixin, AuthenticateTemplateView):
    template_name = "dashboard/main.html"
    layout_nav_key = "DASHBOARD"
    layout_breadcrumb_label = _("DASHBOARD")
