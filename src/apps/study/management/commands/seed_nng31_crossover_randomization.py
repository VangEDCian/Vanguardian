from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.choices import RandomizationSchemeStatusChoice
from apps.study.models import (
    EventDefinition,
    RandomizationArm,
    RandomizationScheme,
    RandomizationSequencePeriod,
)


class Command(BaseCommand):
    help = "Seed NNG31 two-period crossover randomization scheme, sequence arms, and sequence periods."

    def add_arguments(self, parser):
        parser.add_argument("--study-id", required=True, type=int)
        parser.add_argument("--study-version", required=True)
        parser.add_argument("--actor-id", type=int, default=None)
        parser.add_argument("--period1-start-code", default="")
        parser.add_argument("--period1-end-code", default="")
        parser.add_argument("--period2-start-code", default="")
        parser.add_argument("--period2-end-code", default="")

    def handle(self, *args, **options):
        study_id = options["study_id"]
        study_version = options["study_version"]
        actor_id = options["actor_id"]
        now = timezone.now()

        scheme = self._upsert_scheme(study_id=study_id, actor_id=actor_id, now=now)
        arms = {
            "SEQ_E_N": self._upsert_arm(
                scheme=scheme,
                arm_code="SEQ_E_N",
                arm_name="Eprex -> NANOKINE",
                target_count=22,
                display_order=1,
                actor_id=actor_id,
                now=now,
            ),
            "SEQ_N_E": self._upsert_arm(
                scheme=scheme,
                arm_code="SEQ_N_E",
                arm_name="NANOKINE -> Eprex",
                target_count=22,
                display_order=2,
                actor_id=actor_id,
                now=now,
            ),
        }
        event_ids = self._resolve_event_ids(study_id=study_id, study_version=study_version, options=options)
        self._upsert_sequence_period(
            scheme=scheme,
            arm=arms["SEQ_E_N"],
            period_no=1,
            treatment_code="EPREX",
            start_event_definition_id=event_ids["period1_start"],
            end_event_definition_id=event_ids["period1_end"],
            actor_id=actor_id,
            now=now,
        )
        self._upsert_sequence_period(
            scheme=scheme,
            arm=arms["SEQ_E_N"],
            period_no=2,
            treatment_code="NANOKINE",
            start_event_definition_id=event_ids["period2_start"],
            end_event_definition_id=event_ids["period2_end"],
            actor_id=actor_id,
            now=now,
        )
        self._upsert_sequence_period(
            scheme=scheme,
            arm=arms["SEQ_N_E"],
            period_no=1,
            treatment_code="NANOKINE",
            start_event_definition_id=event_ids["period1_start"],
            end_event_definition_id=event_ids["period1_end"],
            actor_id=actor_id,
            now=now,
        )
        self._upsert_sequence_period(
            scheme=scheme,
            arm=arms["SEQ_N_E"],
            period_no=2,
            treatment_code="EPREX",
            start_event_definition_id=event_ids["period2_start"],
            end_event_definition_id=event_ids["period2_end"],
            actor_id=actor_id,
            now=now,
        )
        self.stdout.write(self.style.SUCCESS("NNG31 crossover randomization seed completed."))

    @staticmethod
    def _upsert_scheme(*, study_id, actor_id, now):
        scheme, created = RandomizationScheme.objects.get_or_create(
            study_id=study_id,
            code="NNG31_XOVER",
            defaults={
                "created_at": now,
                "updated_at": now,
                "deleted": False,
                "name": "NNG31 two-period crossover randomization",
                "randomization_type": "blocked",
                "allocation_ratio_json": {"SEQ_E_N": 1, "SEQ_N_E": 1},
                "target_randomized_total": 44,
                "eligibility_rule_code": None,
                "requires_screening_pass": True,
                "is_open_label": True,
                "status": RandomizationSchemeStatusChoice.ACTIVE,
                "created_by_id": actor_id,
            },
        )
        scheme.name = "NNG31 two-period crossover randomization"
        scheme.randomization_type = "blocked"
        scheme.allocation_ratio_json = {"SEQ_E_N": 1, "SEQ_N_E": 1}
        scheme.target_randomized_total = 44
        scheme.requires_screening_pass = True
        scheme.is_open_label = True
        scheme.status = RandomizationSchemeStatusChoice.ACTIVE
        scheme.updated_at = now
        scheme.save(
            update_fields=[
                "name",
                "randomization_type",
                "allocation_ratio_json",
                "target_randomized_total",
                "requires_screening_pass",
                "is_open_label",
                "status",
                "updated_at",
            ]
        )
        return scheme

    @staticmethod
    def _upsert_arm(*, scheme, arm_code, arm_name, target_count, display_order, actor_id, now):
        arm, _ = RandomizationArm.objects.get_or_create(
            scheme=scheme,
            arm_code=arm_code,
            defaults={
                "created_at": now,
                "updated_at": now,
                "deleted": False,
                "arm_name": arm_name,
                "target_count": target_count,
                "current_count": 0,
                "display_order": display_order,
                "is_active": True,
            },
        )
        arm.arm_name = arm_name
        arm.target_count = target_count
        arm.display_order = display_order
        arm.is_active = True
        arm.deleted = False
        arm.updated_at = now
        arm.save(update_fields=["arm_name", "target_count", "display_order", "is_active", "deleted", "updated_at"])
        return arm

    @staticmethod
    def _upsert_sequence_period(
        *,
        scheme,
        arm,
        period_no,
        treatment_code,
        start_event_definition_id,
        end_event_definition_id,
        actor_id,
        now,
    ):
        sequence_period, _ = RandomizationSequencePeriod.objects.get_or_create(
            arm=arm,
            period_no=period_no,
            defaults={
                "created_at": now,
                "updated_at": now,
                "deleted": False,
                "scheme": scheme,
                "treatment_code": treatment_code,
                "start_event_definition_id": start_event_definition_id,
                "end_event_definition_id": end_event_definition_id,
                "display_order": period_no,
            },
        )
        sequence_period.scheme = scheme
        sequence_period.treatment_code = treatment_code
        sequence_period.start_event_definition_id = start_event_definition_id
        sequence_period.end_event_definition_id = end_event_definition_id
        sequence_period.display_order = period_no
        sequence_period.deleted = False
        sequence_period.updated_at = now
        sequence_period.save(
            update_fields=[
                "scheme",
                "treatment_code",
                "start_event_definition_id",
                "end_event_definition_id",
                "display_order",
                "deleted",
                "updated_at",
            ]
        )
        return sequence_period

    def _resolve_event_ids(self, *, study_id, study_version, options):
        return {
            "period1_start": self._resolve_event_id(
                study_id=study_id,
                study_version=study_version,
                code=options["period1_start_code"],
            ),
            "period1_end": self._resolve_event_id(
                study_id=study_id,
                study_version=study_version,
                code=options["period1_end_code"],
            ),
            "period2_start": self._resolve_event_id(
                study_id=study_id,
                study_version=study_version,
                code=options["period2_start_code"],
            ),
            "period2_end": self._resolve_event_id(
                study_id=study_id,
                study_version=study_version,
                code=options["period2_end_code"],
            ),
        }

    @staticmethod
    def _resolve_event_id(*, study_id, study_version, code):
        code = str(code or "").strip()
        if not code:
            return None
        return (
            EventDefinition.objects.filter(
                study_id=study_id,
                study_version=study_version,
                code__iexact=code,
                deleted=False,
            )
            .values_list("id", flat=True)
            .first()
        )
