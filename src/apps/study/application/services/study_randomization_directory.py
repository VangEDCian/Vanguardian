import json
from collections import Counter

from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _

from apps.study.domain import RandomizationSlot
from apps.study.infrastructure.repositories import DjangoStudyDirectoryRepository


class StudyRandomizationDirectoryQueryService:
    repository_class = DjangoStudyDirectoryRepository
    randomization_scheme_headers = (
        {"label": _("CODE")},
        {"label": _("NAME")},
        {"label": _("TYPE")},
        {"label": _("ALLOCATION RATIO")},
        {"label": _("TARGET TOTAL")},
        {"label": _("ELIGIBILITY RULE")},
        {"label": _("REQUIRES SCREENING PASS")},
        {"label": _("IS OPEN LABEL")},
        {"label": _("STATUS")},
        {"label": _("EFFECTIVE FROM")},
        {"label": _("EFFECTIVE TO")},
        {"label": _("CREATED BY")},
        {"label": _("APPROVED BY")},
        {"label": _("NOTES")},
        {"label": _("CREATED AT")},
        {"label": _("UPDATED AT")},
    )
    randomization_arm_headers = (
        {"label": _("SCHEME")},
        {"label": _("ARM CODE")},
        {"label": _("ARM NAME")},
        {"label": _("TARGET COUNT")},
        {"label": _("CURRENT COUNT")},
        {"label": _("ORDER")},
        {"label": _("ACTIVE")},
        {"label": _("NOTES")},
        {"label": _("CREATED AT")},
        {"label": _("UPDATED AT")},
    )
    randomization_slot_headers = (
        {"label": _("SCHEME")},
        {"label": _("SEQUENCE")},
        {"label": _("ARM")},
        {"label": _("STATUS")},
        {"label": _("BLOCK")},
        {"label": _("SUBJECT ID")},
        {"label": _("ASSIGNED AT")},
        {"label": _("VOID REASON")},
        {"label": _("NOTES")},
    )
    randomization_eligibility_headers = (
        {"label": _("SCHEME")},
        {"label": _("SUBJECT ID")},
        {"label": _("ELIGIBLE")},
        {"label": _("EVALUATED AT")},
        {"label": _("REASON CODE")},
        {"label": _("SCREENING STATUS")},
    )

    def __init__(self, repository=None):
        self.repository = repository or self.repository_class()

    def get_overview(self, *, study_id):
        schemes = list(self.repository.list_randomization_schemes(study_id=study_id))
        arms = list(self.repository.list_randomization_arms(study_id=study_id))
        slots = list(self.repository.list_randomization_slots(study_id=study_id))
        eligibilities = list(self.repository.list_randomization_eligibilities(study_id=study_id))

        return {
            "randomization_scheme_headers": self.randomization_scheme_headers,
            "randomization_scheme_rows": [
                self._build_scheme_row(scheme) for scheme in schemes
            ],
            "randomization_scheme_total": len(schemes),
            "randomization_scheme_empty_text": _(
                "No randomization schemes have been configured for this study."
            ),
            "randomization_arm_headers": self.randomization_arm_headers,
            "randomization_arm_rows": [self._build_arm_row(arm) for arm in arms],
            "randomization_arm_total": len(arms),
            "randomization_arm_empty_text": _(
                "No randomization arms have been configured for this study."
            ),
            "randomization_slot_headers": self.randomization_slot_headers,
            "randomization_slot_rows": [self._build_slot_row(slot) for slot in slots],
            "randomization_slot_total": len(slots),
            "randomization_slot_status_summary": self._build_slot_status_summary(slots),
            "randomization_slot_empty_text": _(
                "No randomization slots have been configured for this study."
            ),
            "randomization_eligibility_headers": self.randomization_eligibility_headers,
            "randomization_eligibility_rows": [
                self._build_eligibility_row(eligibility)
                for eligibility in eligibilities
            ],
            "randomization_eligibility_total": len(eligibilities),
            "randomization_eligibility_empty_text": _(
                "No eligibility policy records have been captured for this study."
            ),
        }

    def _build_scheme_row(self, scheme):
        return {
            "selection_value": scheme.pk,
            "cells": [
                {
                    "kind": "text",
                    "value": scheme.code,
                    "column_class": "entity-table__primary",
                },
                self._build_text_cell(
                    scheme.name,
                    column_class="entity-table__wrap entity-table__scheme-name",
                ),
                self._build_text_cell(
                    self._humanize_choice_value(scheme.randomization_type)
                ),
                self._build_text_cell(
                    json.dumps(scheme.allocation_ratio_json, ensure_ascii=True)
                    if scheme.allocation_ratio_json not in (None, "")
                    else ""
                ),
                self._build_text_cell(str(scheme.target_randomized_total)),
                self._build_text_cell(scheme.eligibility_rule_code),
                self._build_boolean_state_cell(scheme.requires_screening_pass),
                self._build_boolean_state_cell(scheme.is_open_label),
                self._build_text_cell(self._humanize_choice_value(scheme.status)),
                self._build_datetime_cell(scheme.effective_from),
                self._build_datetime_cell(scheme.effective_to),
                self._build_text_cell(
                    str(scheme.created_by_id)
                    if scheme.created_by_id is not None
                    else ""
                ),
                self._build_text_cell(
                    str(scheme.approved_by_id)
                    if scheme.approved_by_id is not None
                    else ""
                ),
                self._build_expandable_text_cell(
                    scheme.notes,
                    column_class="entity-table__scheme-notes",
                ),
                self._build_datetime_cell(scheme.created_at),
                self._build_datetime_cell(scheme.updated_at),
            ],
        }

    def _build_arm_row(self, arm):
        return {
            "selection_value": arm.pk,
            "cells": [
                self._build_text_cell(arm.scheme.code if arm.scheme_id else ""),
                {
                    "kind": "text",
                    "value": arm.arm_code,
                    "column_class": "entity-table__primary",
                },
                self._build_text_cell(arm.arm_name, column_class="entity-table__wrap"),
                self._build_text_cell(str(arm.target_count)),
                self._build_text_cell(str(arm.current_count)),
                self._build_text_cell(str(arm.display_order)),
                {
                    "kind": "state",
                    "value": _("Active") if arm.is_active else _("Inactive"),
                    "tone": "active" if arm.is_active else "inactive",
                },
                self._build_expandable_text_cell(
                    arm.notes,
                    column_class="entity-table__arm-notes",
                ),
                self._build_datetime_cell(arm.created_at),
                self._build_datetime_cell(arm.updated_at),
            ],
        }

    def _build_slot_row(self, slot):
        return {
            "selection_value": slot.pk,
            "cells": [
                self._build_text_cell(slot.scheme.code if slot.scheme_id else ""),
                self._build_text_cell(str(slot.sequence_no)),
                self._build_text_cell(slot.arm.arm_code if slot.arm_id else ""),
                self._build_text_cell(self._humanize_choice_value(slot.status)),
                self._build_text_cell(
                    str(slot.block_no) if slot.block_no is not None else ""
                ),
                self._build_text_cell(
                    str(slot.assigned_subject_id)
                    if slot.assigned_subject_id is not None
                    else ""
                ),
                self._build_text_cell(
                    date_format(slot.assigned_at, "DATETIME_FORMAT")
                    if slot.assigned_at
                    else ""
                ),
                self._build_text_cell(slot.void_reason),
                self._build_expandable_text_cell(slot.notes, column_class="entity-table__slot-notes"),
            ],
        }

    @staticmethod
    def _build_slot_status_summary(slots):
        status_counter = Counter(slot.status for slot in slots)
        return (
            {
                "key": RandomizationSlot.AVAILABLE,
                "label": _("Available"),
                "count": status_counter.get(RandomizationSlot.AVAILABLE, 0),
            },
            {
                "key": RandomizationSlot.ASSIGNED,
                "label": _("Assigned"),
                "count": status_counter.get(RandomizationSlot.ASSIGNED, 0),
            },
            {
                "key": RandomizationSlot.VOID,
                "label": _("Void"),
                "count": status_counter.get(RandomizationSlot.VOID, 0),
            },
        )

    def _build_eligibility_row(self, eligibility):
        return {
            "selection_value": eligibility.pk,
            "cells": [
                self._build_text_cell(
                    eligibility.scheme.code if eligibility.scheme_id else ""
                ),
                self._build_text_cell(str(eligibility.subject_id)),
                {
                    "kind": "state",
                    "value": _("Eligible")
                    if eligibility.is_eligible
                    else _("Ineligible"),
                    "tone": "active" if eligibility.is_eligible else "inactive",
                },
                self._build_text_cell(
                    date_format(eligibility.evaluated_at, "DATETIME_FORMAT")
                    if eligibility.evaluated_at
                    else ""
                ),
                self._build_text_cell(eligibility.reason_code),
                self._build_text_cell(eligibility.screening_status_snapshot),
            ],
        }

    @staticmethod
    def _build_text_cell(value, *, column_class=None):
        if value not in (None, ""):
            cell = {"kind": "text", "value": value}
        else:
            cell = {"kind": "muted", "value": "—"}
        if column_class:
            cell["column_class"] = column_class
        return cell

    @staticmethod
    def _build_expandable_text_cell(value, *, column_class=None):
        if value in (None, ""):
            return StudyRandomizationDirectoryQueryService._build_text_cell(
                value,
                column_class=column_class,
            )
        cell = {"kind": "expandable_text", "value": str(value)}
        if column_class:
            cell["column_class"] = column_class
        return cell

    @staticmethod
    def _build_datetime_cell(value):
        if value:
            return {"kind": "text", "value": date_format(value, "DATETIME_FORMAT")}
        return {"kind": "muted", "value": "-"}

    @staticmethod
    def _build_boolean_state_cell(value):
        is_active = bool(value)
        return {
            "kind": "state",
            "value": _("Yes") if is_active else _("No"),
            "tone": "active" if is_active else "inactive",
        }

    @staticmethod
    def _humanize_choice_value(value):
        if not value:
            return ""
        return str(value).replace("_", " ").replace("-", " ").title()
