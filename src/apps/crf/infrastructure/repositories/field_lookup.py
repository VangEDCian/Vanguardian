from django.db.models import Q

from apps.crf.models import CrfFieldLookup


class DjangoCrfFieldLookupRepository:
    def search_values(self, *, lookup_key: str, query: str = "", limit: int = 20) -> list[dict]:
        queryset = CrfFieldLookup.objects.filter(deleted=False, key=lookup_key)
        if query:
            queryset = queryset.filter(Q(label__icontains=query) | Q(value__icontains=query.upper()))

        return [
            {
                "value": row.value,
                "label": row.label,
            }
            for row in queryset.order_by("label", "value")[:limit]
        ]
