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
    arm = tables.Column(
        empty_values=(),
        verbose_name=_("ARM"),
        orderable=False,
    )
    completion = tables.Column(
        empty_values=(),
        verbose_name=_("Completion"),
        orderable=False,
    )
    open_queries = tables.Column(
        empty_values=(),
        verbose_name=_("Open Queries"),
        orderable=False,
    )
    validation_issues = tables.Column(
        empty_values=(),
        verbose_name=_("Validation Issues"),
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
        self.workflow_action_event_id_by_subject_id = (
            kwargs.pop("workflow_action_event_id_by_subject_id", None) or {}
        )
        self.can_update_subject = kwargs.pop("can_update_subject", False)
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

    def render_arm(self, record):
        try:
            arm_name = record.randomization.arm.arm_name
        except (AttributeError, ObjectDoesNotExist):
            return "—"
        return arm_name or "—"

    @staticmethod
    def render_completion(record):
        return "—"

    @staticmethod
    def render_open_queries(record):
        return int(getattr(record, "open_query_count", 0) or 0)

    @staticmethod
    def render_validation_issues(record):
        return int(getattr(record, "validation_issue_count", 0) or 0)

    class Meta:
        model = get_subject_list_row_model()
        fields = (
            "subject_code",
            "screening_code",
            "screening",
            "enrollment",
            "randomization",
            "arm",
            "completion",
            "open_queries",
            "validation_issues",
            "actions",
        )
