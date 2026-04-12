import django_tables2 as tables

from django.core.exceptions import ObjectDoesNotExist
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _

from apps.subject.models import Subject


class SubjectListTable(tables.Table):
    subject_code = tables.Column(
        verbose_name=_("Subject"),
        attrs={"td": {"class": "entity-table__primary"}},
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
            "enrollment",
            "randomization",
            "completion",
            "query_status",
        )
