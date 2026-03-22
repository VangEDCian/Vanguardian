from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class DashboardMainView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/main.html"
