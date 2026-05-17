import django_tables2 as tables
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _

from apps.subject.presentation.web.mappers.subject_list_model import get_subject_list_row_model


class SubjectListTable(tables.Table):
    subject_code = tables.Column(
        verbose_name=_("Subject"),
        attrs={"td": {"class": "entity-table__primary"}},
        empty_values=(),
        linkify=lambda record: reverse(
            "subject:subject_detail",
            kwargs={"study_id": record.study_id, "subject_id": record.pk},
        ),
    )
    screening_code = tables.Column(
        verbose_name=_("SCREENING CODE"),
    )
    screening = tables.Column(
        empty_values=(),
        verbose_name=_("SCREENING"),
        orderable=False,
    )
    enrollment = tables.Column(
        empty_values=(),
        verbose_name=_("Enrollment"),
        orderable=False,
    )
    randomization = tables.Column(
        empty_values=(),
        verbose_name=_("Randomization"),
        orderable=False,
    )
    completion = tables.Column(
        empty_values=(),
        verbose_name=_("Completion"),
        orderable=False,
    )
    query_status = tables.Column(
        empty_values=(),
        verbose_name=_("Query Status"),
        orderable=False,
    )
    actions = tables.TemplateColumn(
        template_name="subject/includes/subject_list_actions_cell.html",
        verbose_name=_("ACTIONS"),
        empty_values=(),
        orderable=False,
        attrs={"td": {"class": "entity-table__actions"}},
    )

    def __init__(self, *args, **kwargs):
        self._verify_show_by_subject_id = kwargs.pop("verify_show_by_subject_id", None) or {}
        # For template: {% if record.pk in table.verify_eligible_subject_ids %} (no custom filter).
        self.verify_eligible_subject_ids = frozenset(
            sid for sid, ok in self._verify_show_by_subject_id.items() if ok
        )
        super().__init__(*args, **kwargs)

    @staticmethod
    def render_subject_code(record):
        return record.subject_code or record.screening_code or "—"

    @staticmethod
    def render_screening(record):
        return date_format(record.created_at, "DATETIME_FORMAT") if record.created_at else "—"

    def render_enrollment(self, record):
        try:
            created_at = record.enrollment.created_at
        except ObjectDoesNotExist:
            return "—"
        return date_format(created_at, "DATETIME_FORMAT") if created_at else "—"

    def render_randomization(self, record):
        try:
            created_at = record.randomization.created_at
        except ObjectDoesNotExist:
            return "—"
        return date_format(created_at, "DATETIME_FORMAT") if created_at else "—"

    @staticmethod
    def render_completion(record):
        return "—"

    @staticmethod
    def render_query_status(record):
        return "—"

    class Meta:
        model = get_subject_list_row_model()
        fields = (
            "subject_code",
            "screening_code",
            "screening",
            "enrollment",
            "randomization",
            "completion",
            "query_status",
            "actions",
        )
