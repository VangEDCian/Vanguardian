__all__ = [
    'SitesFilter',
]

from apps.shared.application.queries.shared_filters import SharedIsActiveFilter, SharedSearchFilter
from apps.study.infrastructure.persistence.models import Site


class SitesFilter(SharedIsActiveFilter, SharedSearchFilter):
    SEARCH_FIELDS = ("name", "code")

    class Meta:
        model = Site
        fields = ('is_active', 'search',)
