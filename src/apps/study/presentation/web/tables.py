import django_tables2 as tables

from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.study.infrastructure.persistence.models import Site


class SiteListTable(tables.Table):
    code = tables.Column(
        linkify=("study:site_detail", {"site_id": tables.A("pk"), 'study_id': tables.A("study_id")}),
        attrs={"td": {"class": "entity-table__primary is-detailed"}},
    )
    is_active = tables.Column(
        accessor="is_active",
        verbose_name=_("Status"),
        order_by=("is_active", "code"),
    )

    def render_is_active(self, value):
        tone = "active" if value else "inactive"
        label = _("Active") if value else _("Inactive")
        return format_html(
            '<span class="entity-table__state entity-table__state--{}">'
            '<span class="svg-icon" aria-hidden="true" style="--icon-url: url(\'{}\')"></span>'
            "{}"
            "</span>",
            tone,
            static("images/status/activate.svg"),
            label,
        )

    class Meta:
        model = Site
        fields = ("code", "name", "investigator", "is_active")
