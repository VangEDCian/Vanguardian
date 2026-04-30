from django.urls import path

from apps.crf.presentation.api.views import CrfFormBuilderTreeApiView

urlpatterns = [
    path("forms/<int:form_id>/builder/tree", CrfFormBuilderTreeApiView.as_view(), name="form_builder_tree_api"),
]
