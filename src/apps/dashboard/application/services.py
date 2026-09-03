from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.choices.study import EventInstanceStatusChoices, RandomizationSlotStatusChoice
from apps.reconcile.application.services.query_workbench import QueryWorkbenchReader, QueryWorkbenchSummaryDTO
from apps.study.models import RandomizationScheme, RandomizationSlot, Site
from apps.subject.models import Subject, SubjectEnrollment, SubjectEventInstance, SubjectRandomization


class DashboardOverviewService:
    query_workbench_reader_class = QueryWorkbenchReader

    def build(self, *, user, study_id: int | None, site_id: int | None = None):
        sites = self._list_sites(study_id=study_id)
        selected_site = self._resolve_selected_site(sites=sites, site_id=site_id)
        resolved_site_id = selected_site.pk if selected_site is not None else None

        query_summary = self._get_query_summary(user=user, study_id=study_id, site_id=resolved_site_id)
        scope_counts = self._get_scope_counts(study_id=study_id, site_id=resolved_site_id)
        subject_counts = self._get_subject_counts(study_id=study_id, site_id=resolved_site_id)
        visit_counts = self._get_visit_counts(study_id=study_id, site_id=resolved_site_id)
        randomization_counts = self._get_randomization_counts(study_id=study_id, site_id=resolved_site_id)

        return {
            "dashboard_scope_summary": {
                "scope_label": selected_site.name if selected_site is not None else str(_("All Sites")),
                "scope_code": selected_site.code if selected_site is not None else str(_("Study Total")),
                "selected_site_id": resolved_site_id,
                "study_site_count": len(sites),
                "active_site_count": scope_counts["active_sites"],
            },
            "dashboard_site_filter_options": self._build_site_filter_options(
                sites=sites,
                selected_site_id=resolved_site_id,
            ),
            "dashboard_overview_cards": (
                {
                    "label": _("Subjects in Scope"),
                    "value": subject_counts["subjects"],
                    "accent_class": "dashboard-kpi-card__accent--blue",
                },
                {
                    "label": _("Enrolled Subjects"),
                    "value": subject_counts["enrolled"],
                    "accent_class": "dashboard-kpi-card__accent--green",
                },
                {
                    "label": _("Randomized Subjects"),
                    "value": subject_counts["randomized"],
                    "accent_class": "dashboard-kpi-card__accent--amber",
                },
                {
                    "label": _("Overdue Visits"),
                    "value": visit_counts["overdue"],
                    "accent_class": "dashboard-kpi-card__accent--rose",
                },
            ),
            "dashboard_query_rows": (
                {
                    "label": _("Open"),
                    "count": query_summary.open,
                    "icon_class": "dashboard-query-summary__icon--rose",
                },
                {
                    "label": _("Waiting CRA Review"),
                    "count": query_summary.awaiting_review,
                    "icon_class": "dashboard-query-summary__icon--amber",
                },
                {
                    "label": _("Blocking"),
                    "count": query_summary.blocking_open,
                    "icon_class": "dashboard-query-summary__icon--slate",
                },
                {
                    "label": _("Resolved"),
                    "count": query_summary.resolved,
                    "icon_class": "dashboard-query-summary__icon--outline",
                },
                {
                    "label": _("Closed"),
                    "count": query_summary.closed,
                    "icon_class": "dashboard-query-summary__icon--slate",
                },
            ),
            "dashboard_query_total": query_summary.total,
            "dashboard_enrollment_rows": (
                {"label": _("Active Sites"), "count": scope_counts["active_sites"]},
                {"label": _("Enrolled"), "count": subject_counts["enrolled"]},
                {"label": _("Not Yet Enrolled"), "count": subject_counts["not_enrolled"]},
                {"label": _("Withdrawn"), "count": subject_counts["withdrawn"]},
                {"label": _("Screen Failed"), "count": subject_counts["screen_failed"]},
            ),
            "dashboard_execution_rows": (
                {"label": _("Open Visits"), "count": visit_counts["open"]},
                {"label": _("In Progress"), "count": visit_counts["in_progress"]},
                {"label": _("Completed"), "count": visit_counts["completed"]},
                {"label": _("Verified / Locked"), "count": visit_counts["verified_locked"]},
                {"label": _("Overdue"), "count": visit_counts["overdue"]},
            ),
            "dashboard_randomization_rows": (
                {"label": _("Enrolled"), "count": randomization_counts["enrolled"]},
                {"label": _("Randomized"), "count": randomization_counts["randomized"]},
                {"label": _("Awaiting Randomization"), "count": randomization_counts["awaiting_randomization"]},
                {"label": _("Schemes"), "count": self._count_randomization_schemes(study_id=study_id)},
                {"label": _("Available Study Slots"), "count": self._count_available_randomization_slots(study_id=study_id)},
            ),
            "dashboard_priority_rows": self._build_priority_rows(
                query_summary=query_summary,
                visit_counts=visit_counts,
                randomization_counts=randomization_counts,
                subject_counts=subject_counts,
            ),
        }

    @staticmethod
    def _list_sites(*, study_id: int | None):
        if study_id is None:
            return ()
        return tuple(
            Site.objects.filter(study_id=study_id, deleted=False)
            .only("id", "code", "name", "is_active")
            .order_by("id")
        )

    @staticmethod
    def _resolve_selected_site(*, sites, site_id: int | None):
        if site_id is None:
            return None
        for site in sites:
            if int(site.pk) == int(site_id):
                return site
        return None

    @staticmethod
    def _build_site_filter_options(*, sites, selected_site_id: int | None):
        options = [
            {
                "value": "",
                "label": str(_("All Sites")),
                "selected": selected_site_id is None,
            }
        ]
        for site in sites:
            options.append(
                {
                    "value": str(site.pk),
                    "label": f"{site.code} - {site.name}",
                    "selected": selected_site_id is not None and int(selected_site_id) == int(site.pk),
                }
            )
        return tuple(options)

    def _get_query_summary(self, *, user, study_id: int | None, site_id: int | None = None):
        if study_id is None:
            return self._empty_query_summary()
        return self.query_workbench_reader_class().read(
            study_id=study_id,
            site_id=site_id,
            current_user_id=getattr(user, "pk", None),
            can_view_internal_thread=False,
        ).summary

    @staticmethod
    def _get_scope_counts(*, study_id: int | None, site_id: int | None = None):
        if study_id is None:
            return {"active_sites": 0}
        filters = Q(study_id=study_id, deleted=False, is_active=True)
        if site_id is not None:
            filters &= Q(pk=site_id)
        return {"active_sites": Site.objects.filter(filters).count()}

    @staticmethod
    def _get_subject_counts(*, study_id: int | None, site_id: int | None = None):
        if study_id is None:
            return {
                "subjects": 0,
                "enrolled": 0,
                "not_enrolled": 0,
                "withdrawn": 0,
                "screen_failed": 0,
                "randomized": 0,
            }

        subject_filters = Q(study_id=study_id, deleted=False)
        enrollment_filters = Q(study_id=study_id, deleted=False)
        randomization_filters = Q(study_id=study_id, deleted=False)
        if site_id is not None:
            subject_filters &= Q(site_id=site_id)
            enrollment_filters &= Q(site_id=site_id)
            randomization_filters &= Q(site_id=site_id)

        return {
            "subjects": Subject.objects.filter(subject_filters).count(),
            "enrolled": SubjectEnrollment.objects.filter(enrollment_filters, is_enrolled=True).count(),
            "not_enrolled": SubjectEnrollment.objects.filter(enrollment_filters, is_enrolled=False).count(),
            "withdrawn": SubjectEnrollment.objects.filter(enrollment_filters, withdrawn_at__isnull=False).count(),
            "screen_failed": SubjectEnrollment.objects.filter(
                enrollment_filters,
                screen_failed_at__isnull=False,
            ).count(),
            "randomized": SubjectRandomization.objects.filter(
                randomization_filters,
                slot_id__isnull=False,
            ).count(),
        }

    @staticmethod
    def _get_visit_counts(*, study_id: int | None, site_id: int | None = None):
        if study_id is None:
            return {
                "open": 0,
                "in_progress": 0,
                "completed": 0,
                "verified_locked": 0,
                "overdue": 0,
            }

        filters = Q(study_id=study_id, deleted=False)
        if site_id is not None:
            filters &= Q(subject__site_id=site_id)
        queryset = SubjectEventInstance.objects.filter(filters)
        completed_statuses = (
            EventInstanceStatusChoices.COMPLETED,
            EventInstanceStatusChoices.VERIFIED,
            EventInstanceStatusChoices.LOCKED,
            EventInstanceStatusChoices.FINALIZED,
            EventInstanceStatusChoices.SKIPPED,
            EventInstanceStatusChoices.CANCELLED,
        )
        return {
            "open": queryset.filter(status=EventInstanceStatusChoices.OPEN).count(),
            "in_progress": queryset.filter(status=EventInstanceStatusChoices.IN_PROGRESS).count(),
            "completed": queryset.filter(status=EventInstanceStatusChoices.COMPLETED).count(),
            "verified_locked": queryset.filter(
                status__in=(
                    EventInstanceStatusChoices.VERIFIED,
                    EventInstanceStatusChoices.LOCKED,
                    EventInstanceStatusChoices.FINALIZED,
                )
            ).count(),
            "overdue": queryset.filter(target_date__lt=timezone.now()).exclude(
                status__in=completed_statuses
            ).count(),
        }

    @staticmethod
    def _get_randomization_counts(*, study_id: int | None, site_id: int | None = None):
        if study_id is None:
            return {
                "enrolled": 0,
                "randomized": 0,
                "awaiting_randomization": 0,
            }

        filters = Q(study_id=study_id, deleted=False)
        if site_id is not None:
            filters &= Q(site_id=site_id)
        enrolled = SubjectEnrollment.objects.filter(filters, is_enrolled=True).count()
        randomized = SubjectRandomization.objects.filter(filters, slot_id__isnull=False).count()
        return {
            "enrolled": enrolled,
            "randomized": randomized,
            "awaiting_randomization": max(enrolled - randomized, 0),
        }

    @staticmethod
    def _count_randomization_schemes(*, study_id: int | None):
        if study_id is None:
            return 0
        return RandomizationScheme.objects.filter(study_id=study_id, deleted=False).count()

    @staticmethod
    def _count_available_randomization_slots(*, study_id: int | None):
        if study_id is None:
            return 0
        return RandomizationSlot.objects.filter(
            scheme__study_id=study_id,
            scheme__deleted=False,
            deleted=False,
            status=RandomizationSlotStatusChoice.AVAILABLE,
        ).count()

    def _build_priority_rows(
        self,
        *,
        query_summary: QueryWorkbenchSummaryDTO,
        visit_counts: dict[str, int],
        randomization_counts: dict[str, int],
        subject_counts: dict[str, int],
    ):
        priorities = []
        if query_summary.blocking_open:
            priorities.append(
                {
                    "tone": "critical",
                    "title": _("Resolve blocking queries"),
                    "detail": _("There are %(count)s blocking queries holding up downstream review or lock work.")
                    % {"count": query_summary.blocking_open},
                }
            )
        if visit_counts["overdue"]:
            priorities.append(
                {
                    "tone": "warning",
                    "title": _("Triage overdue visits"),
                    "detail": _("%(count)s visit instances are past target date and still not finished.")
                    % {"count": visit_counts["overdue"]},
                }
            )
        if query_summary.validation_issues_open:
            priorities.append(
                {
                    "tone": "warning",
                    "title": _("Clear validation backlog"),
                    "detail": _("%(count)s open validation issues still need acknowledgement or correction.")
                    % {"count": query_summary.validation_issues_open},
                }
            )
        if randomization_counts["enrolled"] and randomization_counts["awaiting_randomization"]:
            priorities.append(
                {
                    "tone": "info",
                    "title": _("Convert enrolled subjects"),
                    "detail": _("%(count)s enrolled subjects are still awaiting randomization.")
                    % {"count": randomization_counts["awaiting_randomization"]},
                }
            )
        if subject_counts["subjects"] and subject_counts["enrolled"] == 0:
            priorities.append(
                {
                    "tone": "info",
                    "title": _("Convert screened subjects"),
                    "detail": _("Subjects exist in scope but none are enrolled yet."),
                }
            )
        if not priorities:
            priorities.append(
                {
                    "tone": "good",
                    "title": _("No immediate operational alerts"),
                    "detail": _("Enrollment, data quality, and execution indicators look stable in the current scope."),
                }
            )
        return tuple(priorities)

    @staticmethod
    def _empty_query_summary():
        return QueryWorkbenchSummaryDTO(
            total=0,
            open=0,
            awaiting_site_response=0,
            awaiting_review=0,
            blocking_open=0,
            resolved=0,
            closed=0,
            validation_issues_open=0,
            hard_validation_issues_open=0,
            actionable_for_current_user=0,
        )
