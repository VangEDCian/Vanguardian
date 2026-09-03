import django_tables2 as tables
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.crf.public import get_crf_template_model
from apps.shared.datetime_formatting import date_format
from apps.study.infrastructure.persistence.models import EventDefinition, Site


class SiteListTable(tables.Table):
    code = tables.Column(
        linkify=("study:site_detail", {"site_id": tables.A("pk"), "study_id": tables.A("study_id")}),
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

    @staticmethod
    def render_investigator(record):
        investigator = getattr(record, "investigator", None)
        if investigator is None:
            return "—"

        full_name = f"{investigator.first_name or ''} {investigator.last_name or ''}".strip()
        if full_name:
            return full_name
        if investigator.display_name:
            return investigator.display_name
        return investigator.username or str(investigator.pk)

    class Meta:
        model = Site
        fields = ("code", "name", "investigator", "is_active")


class CrfTemplateListTable(tables.Table):
    code = tables.Column(
        verbose_name=_("CODE"),
        linkify=("crf:form_builder", {"form_id": tables.A("pk")}),
        attrs={"td": {"class": "entity-table__primary"}},
        order_by=("code", "version"),
    )
    name = tables.Column(
        verbose_name=_("NAME"),
        order_by=("name", "code", "version"),
    )
    version = tables.Column(
        verbose_name=_("VERSION"),
        order_by=("version", "code"),
    )
    status = tables.Column(
        accessor="is_active",
        verbose_name=_("STATUS"),
        order_by=("is_active", "code", "version"),
    )
    updated_at = tables.Column(
        verbose_name=_("UPDATED AT"),
        order_by=("updated_at", "code", "version"),
    )
    actions = tables.Column(
        verbose_name=_("ACTIONS"),
        empty_values=(),
        orderable=False,
        attrs={"td": {"class": "entity-table__actions"}},
    )

    def render_name(self, record):
        value = record.safe_translation_getter("name", default="", any_language=True)
        return value or "—"

    def render_status(self, value):
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

    @staticmethod
    def render_updated_at(value):
        return date_format(value, "DATETIME_FORMAT") if value else "—"

    @staticmethod
    def render_actions(record):
        return format_html(
            '<div class="crf-template-actions" data-dropdown>'
            '<button type="button" class="crf-template-actions__trigger" data-dropdown-trigger aria-expanded="false" aria-label="{}">'
            '<span class="crf-template-actions__value" data-dropdown-value>{}</span>'
            '<span class="svg-icon crf-template-actions__icon" aria-hidden="true" style="--icon-url: url(\'{}\')"></span>'
            '</button>'
            '<div class="crf-template-actions__menu" data-dropdown-menu hidden>'
            '<a class="crf-template-actions__item" href="{}" data-dropdown-option>{}</a>'
            '<a class="crf-template-actions__item" href="{}" data-dropdown-option>{}</a>'
            '</div>',
            _("Open actions menu"),
            _("Actions"),
            static("images/table/ellipsis-vertical-svgrepo-com.svg"),
            reverse("crf:form_detail", kwargs={"form_id": record.pk}),
            _("Detail"),
            reverse("crf:form_builder", kwargs={"form_id": record.pk}),
            _("Form Builder"),
        )

    class Meta:
        model = get_crf_template_model()
        fields = ("code", "name", "version", "status", "updated_at", "actions")


class EventDefinitionListTable(tables.Table):
    code = tables.Column(
        verbose_name=_("CODE"),
        attrs={"td": {"class": "entity-table__primary"}},
        order_by=("study_version", "code"),
    )
    study_version = tables.Column(
        verbose_name=_("VERSION"),
        order_by=("study_version", "sequence_no", "code"),
    )
    name = tables.Column(
        verbose_name=_("NAME"),
        order_by=("study_version", "name", "code"),
    )
    event_type = tables.Column(
        verbose_name=_("EVENT TYPE"),
        order_by=("study_version", "event_type", "sequence_no", "code"),
    )
    timing_mode = tables.Column(
        verbose_name=_("TIMING"),
        order_by=("study_version", "timing_mode", "sequence_no", "code"),
    )
    sequence_no = tables.Column(
        verbose_name=_("SEQUENCE"),
        order_by=("study_version", "sequence_no", "code"),
    )
    required = tables.Column(
        accessor="is_required",
        verbose_name=_("REQUIRED"),
        order_by=("study_version", "is_required", "sequence_no", "code"),
    )
    enabled = tables.Column(
        accessor="is_enabled",
        verbose_name=_("ENABLED"),
        order_by=("study_version", "is_enabled", "sequence_no", "code"),
    )

    @staticmethod
    def render_event_type(record):
        return record.get_event_type_display() if record.event_type else "—"

    @staticmethod
    def render_timing_mode(record):
        return record.get_timing_mode_display() if record.timing_mode else "—"

    def render_required(self, value):
        tone = "active" if value else "inactive"
        label = _("Required") if value else _("Optional")
        return format_html(
            '<span class="entity-table__state entity-table__state--{}">'
            '<span class="svg-icon" aria-hidden="true" style="--icon-url: url(\'{}\')"></span>'
            "{}"
            "</span>",
            tone,
            static("images/status/activate.svg"),
            label,
        )

    def render_enabled(self, value):
        tone = "active" if value else "inactive"
        label = _("Enabled") if value else _("Disabled")
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
        model = EventDefinition
        fields = (
            "code",
            "study_version",
            "name",
            "event_type",
            "timing_mode",
            "sequence_no",
            "required",
            "enabled",
        )
