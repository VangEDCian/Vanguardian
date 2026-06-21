from django.db.models import CharField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Cast, Coalesce, Concat

from apps.identity.models import User
from apps.subject.models import (
    Subject,
    SubjectEventInstanceTransitionLog,
    SubjectStatusHistory,
)


class DjangoSubjectAuditHistoryRepository:
    def get_subject_context(self, *, study_id: int, subject_id: int, snapshot_class):
        subject = (
            Subject.objects.filter(study_id=study_id, pk=subject_id, deleted=False)
            .select_related("study", "site")
            .first()
        )
        if subject is None:
            return None
        return snapshot_class(
            subject_id=int(subject.pk),
            study_id=int(subject.study_id),
            study_code=getattr(subject.study, "code", "") or "",
            study_name=getattr(subject.study, "name", "") or "",
            site_code=getattr(subject.site, "code", "") or "",
            screening_code=subject.screening_code or "",
            subject_code=subject.subject_code or "",
        )

    def list_subject_status_history(
        self,
        *,
        subject_id: int,
        record_class,
        limit: int = 200,
        search: str = "",
        field_name: str = "",
    ):
        queryset = self._annotate_audit_fields(
            SubjectStatusHistory.objects.filter(subject_id=subject_id),
            actor_field="changed_by_id",
            field_name="subject_status",
            field_description=Value("Subject status transition", output_field=CharField()),
            value_expression=Concat(
                Coalesce("from_status", Value("")),
                Value(" "),
                Coalesce("to_status", Value("")),
                Value(" "),
                Coalesce("reason_code", Value("")),
                Value(" "),
                Coalesce("reason_text", Value("")),
                Value(" "),
                Coalesce("source", Value("")),
                output_field=CharField(),
            ),
        )
        queryset = self._apply_audit_filters(queryset, search=search, field_name=field_name)
        queryset = queryset.order_by("-transition_at", "-id")
        if limit:
            queryset = queryset[:limit]
        return [
            record_class(
                occurred_at=row.transition_at,
                field_name=row.audit_field_name,
                field_description=row.audit_field_description,
                value=row.audit_value,
                user_display=row.audit_user_display,
                from_status=row.from_status or "",
                to_status=row.to_status or "",
                reason_code=row.reason_code or "",
                reason_text=row.reason_text or "",
                source=row.source or "",
                actor_id=row.changed_by_id,
            )
            for row in queryset
        ]

    def list_event_instance_transition_history(
        self,
        *,
        study_id: int,
        subject_id: int,
        record_class,
        limit: int = 200,
        search: str = "",
        field_name: str = "",
    ):
        queryset = self._annotate_audit_fields(
            SubjectEventInstanceTransitionLog.objects.filter(
                study_id=study_id,
                subject_id=subject_id,
                deleted=False,
            )
            .select_related(
                "from_event_definition",
                "to_event_definition",
                "source_event_instance",
                "target_event_instance",
                "transition_rule",
            )
            ,
            actor_field="created_by_id",
            field_name="event_transition",
            field_description=Concat(
                Coalesce("source_event_instance__event_name_snapshot", "from_event_definition__name", Value("")),
                Value(" -> "),
                Coalesce("target_event_instance__event_name_snapshot", "to_event_definition__name", Value("")),
                output_field=CharField(),
            ),
            value_expression=Concat(
                Coalesce("from_status", Value("")),
                Value(" "),
                Coalesce("to_status", Value("")),
                Value(" "),
                Coalesce("result", Value("")),
                Value(" "),
                Coalesce("reason", Value("")),
                Value(" "),
                Coalesce("trigger_source", Value("")),
                Value(" "),
                Coalesce("facts_json", Value("")),
                output_field=CharField(),
            ),
        )
        queryset = self._apply_audit_filters(queryset, search=search, field_name=field_name)
        queryset = queryset.order_by("-created_at", "-id")
        if limit:
            queryset = queryset[:limit]

        return [
            record_class(
                occurred_at=row.created_at,
                field_name=row.audit_field_name,
                field_description=row.audit_field_description,
                value=row.audit_value,
                user_display=row.audit_user_display,
                from_event_label=self._event_label(row.source_event_instance, row.from_event_definition),
                to_event_label=self._event_label(row.target_event_instance, row.to_event_definition),
                from_status=row.from_status or "",
                to_status=row.to_status or "",
                trigger_source=row.trigger_source or "",
                result=row.result or "",
                reason=row.reason or "",
                actor_id=row.created_by_id,
                transition_rule_id=row.transition_rule_id,
            )
            for row in queryset
        ]

    @classmethod
    def _annotate_audit_fields(
        cls,
        queryset,
        *,
        actor_field: str,
        field_name: str,
        field_description,
        value_expression,
    ):
        return queryset.annotate(
            audit_field_name=Value(field_name, output_field=CharField()),
            audit_field_description=field_description,
            audit_value=value_expression,
            audit_user_display=cls._user_display_expression(actor_field),
        )

    @classmethod
    def _apply_audit_filters(cls, queryset, *, search: str = "", field_name: str = ""):
        normalized_field_name = str(field_name or "").strip()
        if normalized_field_name:
            queryset = queryset.filter(audit_field_name__icontains=normalized_field_name)

        for term in cls._search_terms(search):
            queryset = queryset.filter(
                Q(audit_value__icontains=term)
                | Q(audit_field_description__icontains=term)
                | Q(audit_user_display__icontains=term)
            )
        return queryset

    @staticmethod
    def _search_terms(search: str) -> tuple[str, ...]:
        normalized_search = str(search or "").strip()
        if not normalized_search:
            return ()
        return tuple(term for term in normalized_search.split() if term)

    @staticmethod
    def _user_display_expression(actor_field: str):
        user_display = (
            User.objects.filter(pk=OuterRef(actor_field), deleted=False)
            .annotate(
                audit_display=Concat(
                    Coalesce("display_name", Value("")),
                    Value(" "),
                    Coalesce("first_name", Value("")),
                    Value(" "),
                    Coalesce("last_name", Value("")),
                    Value(" "),
                    Coalesce("username", Value("")),
                    output_field=CharField(),
                )
            )
            .values("audit_display")[:1]
        )
        return Coalesce(
            Cast(Subquery(user_display), output_field=CharField()),
            Value("System"),
            output_field=CharField(),
        )

    @staticmethod
    def _event_label(event_instance, event_definition) -> str:
        if event_instance is not None:
            label = (
                event_instance.event_name_snapshot
                or getattr(event_definition, "name", "")
                or event_instance.event_code_snapshot
                or getattr(event_definition, "code", "")
            )
            if event_instance.repeat_index and int(event_instance.repeat_index) > 1:
                return f"{label} #{event_instance.repeat_index}" if label else f"Repeat #{event_instance.repeat_index}"
            return label or ""
        return getattr(event_definition, "name", "") or getattr(event_definition, "code", "") or ""


__all__ = ["DjangoSubjectAuditHistoryRepository"]
