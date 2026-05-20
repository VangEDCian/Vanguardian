from apps.audit.infrastructure.persistence.models import AuditEvent
from apps.identity.infrastructure.persistence.models import StudyMembership
from apps.shared.constants.audit_events import AuditEventObjectType
from apps.study.infrastructure.persistence.models import (
    EventDefinition,
    EventTransitionRule,
    RandomizationArm,
    RandomizationScheme,
    RandomizationSlot,
    Site,
    Study,
)


class DjangoStudyDirectoryRepository:
    def list_studies(self, *, order_by=(), user=None):
        queryset = Study.objects.filter(deleted=False).order_by(*order_by)
        if user is not None and not user.is_superuser:
            member_study_ids = StudyMembership.objects.filter(user=user, deleted=False).values_list(
                "study_id",
                flat=True,
            )
            queryset = queryset.filter(pk__in=member_study_ids)
        return queryset

    def get_study(self, *, study_id):
        return Study.objects.filter(pk=study_id, deleted=False).first()

    def list_active_studies(self, *, user):
        return self.list_studies(user=user).order_by("code")

    def list_study_history_events(self, *, study_id):
        return (
            AuditEvent.objects.filter(
                object_type=AuditEventObjectType.STUDY,
                object_id=str(study_id),
                deleted=False,
            )
            .select_related("created_by")
            .order_by("-created_at")
        )

    def list_event_definitions(self, *, study_id):
        return EventDefinition.objects.filter(
            study_id=study_id,
            deleted=False,
        ).order_by("study_version", "sequence_no", "code", "pk")

    def list_event_transition_rules(self, *, study_id):
        return (
            EventTransitionRule.objects.select_related("from_event_definition", "to_event_definition")
            .filter(
                study_id=study_id,
                deleted=False,
                from_event_definition__deleted=False,
                to_event_definition__deleted=False,
            )
            .order_by("study_version", "display_order", "id")
        )

    def list_randomization_schemes(self, *, study_id):
        return RandomizationScheme.objects.filter(
            study_id=study_id,
            deleted=False,
        ).order_by("code")

    def list_randomization_arms(self, *, study_id):
        return (
            RandomizationArm.objects.select_related("scheme")
            .filter(
                scheme__study_id=study_id,
                scheme__deleted=False,
                deleted=False,
            )
            .order_by("scheme_id", "display_order", "arm_code")
        )

    def list_randomization_slots(self, *, study_id):
        return (
            RandomizationSlot.objects.select_related("scheme", "arm")
            .filter(
                scheme__study_id=study_id,
                scheme__deleted=False,
                deleted=False,
            )
            .order_by("scheme__code", "sequence_no", "id")
        )

    def get_site_model(self):
        return Site
