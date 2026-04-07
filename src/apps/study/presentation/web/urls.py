from django.urls import path, include

from apps.study.presentation.web.views import (
    StudyCreateView,
    StudyDeleteView,
    StudyDetailView,
    StudyListView,
    StudyToggleStatusView,
    StudyUpdateView,

    SiteListView,
    SiteDetailView,
    SiteCreateView,
    SiteDeleteView,
)

app_name = "study"

urlpatterns = [
    path("studies", StudyListView.as_view(), name="study_list"),
    path("studies/new", StudyCreateView.as_view(), name="study_create"),
    path("studies/<int:study_id>", StudyDetailView.as_view(), name="study_detail"),
    path("studies/<int:study_id>/delete", StudyDeleteView.as_view(), name="study_delete"),
    path("studies/<int:study_id>/edit", StudyUpdateView.as_view(), name="study_update"),
    path(
        "studies/<int:study_id>/toggle-status", StudyToggleStatusView.as_view(),
        name="study_toggle_status",
    ),
]

urlpatterns += [
    path(
        "studies/sites/", include(
            [
                path("", SiteListView.as_view(), name="site_list"),
                path("new", SiteCreateView.as_view(), name="site_create"),
                path("<int:site_id>", SiteDetailView.as_view(), name="site_detail"),
                path("<int:site_id>/delete", SiteDeleteView.as_view(), name="site_delete"),
            ],
        ),
    ),
]
