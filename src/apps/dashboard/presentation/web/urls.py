from django.urls import path

from apps.dashboard.presentation.web.views import DashboardMainView


app_name = "dashboard"


urlpatterns = [
    path("dashboard/", DashboardMainView.as_view(), name="main"),
]
