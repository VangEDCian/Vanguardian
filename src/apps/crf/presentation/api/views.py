from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

from apps.crf.application.services import CrfFieldLookupQueryService
from apps.identity.presentation.mixins import ContextPermissionRequiredMixin


class CrfFieldLookupValuesAPIView(LoginRequiredMixin, ContextPermissionRequiredMixin, View):
    permission_required = "subject.view_subject_detail"
    authorization_scope = "STUDY_SITE"
    require_study_context = False
    require_site_context = True
    raise_exception = True

    def get(self, request, *args, **kwargs):
        lookup_key = str(request.GET.get("lookup") or "").strip()
        query = str(request.GET.get("q") or "").strip()
        results = [
            {
                "value": row["value"],
                "label": row["label"],
                "id": row["value"],
                "text": row["label"],
            }
            for row in CrfFieldLookupQueryService().search_values(lookup_key=lookup_key, query=query)
        ]
        return JsonResponse({"results": results})
