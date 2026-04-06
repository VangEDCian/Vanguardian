import django_tables2 as tables

from apps.study.infrastructure.persistence.models import Site


class SiteListTable(tables.Table):
    code = tables.Column(linkify=("study:site_detail", {"site_id": tables.A("pk")}))

    class Meta:
        model = Site
        fields = ('code', 'name', 'investigator', 'is_active')
