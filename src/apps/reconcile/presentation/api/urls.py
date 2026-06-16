from django.urls import path

from apps.reconcile.presentation.api.views import QueryLifecycleActionAPIView

app_name = "reconcile_api"

urlpatterns = [
    path(
        "studies/<int:study_id>/queries/<int:query_id>/<str:action>/",
        QueryLifecycleActionAPIView.as_view(),
        name="query_action",
    ),
]
