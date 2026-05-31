from django.urls import path

from apps.reconcile.presentation.web.views import QueryDetailView, QueryWorkbenchView

app_name = "reconcile"

urlpatterns = [
    path("studies/<int:study_id>/queries/", QueryWorkbenchView.as_view(), name="query_workbench"),
    path("studies/<int:study_id>/queries/<int:query_id>/", QueryDetailView.as_view(), name="query_detail"),
]
