from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import JsonResponse
from django.views import View

from apps.crf.application.services import CrfFieldLookupQueryService


class CrfFieldLookupValuesAPIView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "subject.view_subject_detail"
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
