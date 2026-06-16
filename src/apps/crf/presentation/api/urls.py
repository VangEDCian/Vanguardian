from django.urls import path

from apps.crf.presentation.api.views import CrfFieldLookupValuesAPIView

app_name = "crf_api"

urlpatterns = [
    path("fields/values", CrfFieldLookupValuesAPIView.as_view(), name="field_lookup_values"),
]
