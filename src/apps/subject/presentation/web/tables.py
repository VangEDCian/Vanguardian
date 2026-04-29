import django_tables2 as tables
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _

from apps.subject.models import Subject


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
        model = Subject
        fields = (
            "subject_code",
            "screening_code",
            "screening",
            "enrollment",
            "randomization",
            "completion",
            "query_status",
        )
