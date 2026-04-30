from django.urls import path

from apps.crf.presentation.api.views import CrfFormBuilderTreeApiView
from apps.crf.presentation.web.views import CrfFieldUpdateView, CrfFormBuilderView, CrfFormDetailView

app_name = "crf"

urlpatterns = [
    path("forms/<int:form_id>", CrfFormDetailView.as_view(), name="form_detail"),
    path("forms/<int:form_id>/builder", CrfFormBuilderView.as_view(), name="form_builder"),
    path("api/forms/<int:form_id>/builder/tree", CrfFormBuilderTreeApiView.as_view(), name="form_builder_tree_api"),
    path("forms/<int:form_id>/fields", CrfFormBuilderView.as_view(), name="form_field_create"),
    path("fields/<int:field_id>", CrfFieldUpdateView.as_view(), name="field_update"),
]
