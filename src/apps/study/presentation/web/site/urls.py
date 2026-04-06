from django.urls import path

from apps.study.presentation.web.site import views

urlpatterns = [
    # Site CRUD
    path("", views.SiteListView.as_view(), name="site_list"),
    path("new", views.SiteCreateView.as_view(), name="site_create"),
    path("<int:site_id>", views.SiteDetailView.as_view(), name="site_detail"),
    path("<int:site_id>/edit", views.SiteUpdateView.as_view(), name="site_update"),
    path("<int:site_id>/delete", views.SiteDeleteView.as_view(), name="site_delete"),
    # Membership CRUD
    path(
        "<int:site_id>/members", views.SiteMembershipListView.as_view(),
        name="membership_list",
    ),
    path(
        "<int:site_id>/members/new", views.SiteMembershipCreateView.as_view(),
        name="membership_create",
    ),
    path(
        "<int:site_id>/members/<int:membership_id>", views.SiteMembershipDetailView.as_view(),
        name="membership_detail",
    ),
    path(
        "<int:site_id>/members/<int:membership_id>/delete",
        views.SiteMembershipDeleteView.as_view(), name="membership_delete",
    ),
]
