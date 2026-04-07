import django_filters

from apps.study.infrastructure.persistence.models import Site


class SitesFilter(django_filters.FilterSet):
    class Meta:
        model = Site
        fields = ('study', 'is_active')
