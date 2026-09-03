from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from apps.study.models import (
    RandomizationArm,
    RandomizationEvent,
    RandomizationScheme,
    RandomizationSequencePeriod,
    RandomizationSlot,
    Site,
    Study,
)
from apps.subject.models import Subject, SubjectPeriod, SubjectRandomization


class ReconcileNng31RandomizationIdentifiersTests(TestCase):
    def test_migrates_legacy_assignment_and_retires_legacy_scheme(self):
        data = self._create_assignment_fixture(
            source_treatments=("NANOKINE", "EPREX_4000U"),
            target_treatments=("NANOKINE", "EPREX_4000U"),
        )

        with patch(
            "apps.study.management.commands.reconcile_nng31_randomization_identifiers."
            "AuditContextAdapter.record_event"
        ):
            call_command(
                "reconcile_nng31_randomization_identifiers",
                study_id=data["study"].pk,
                actor_id=99,
                apply=True,
                stdout=StringIO(),
            )

        assignment = SubjectRandomization.objects.get(pk=data["assignment"].pk)
        target_slot = RandomizationSlot.objects.get(pk=data["target_slot"].pk)
        source_slot = RandomizationSlot.objects.get(pk=data["source_slot"].pk)
        legacy_scheme = RandomizationScheme.objects.get(pk=data["legacy_scheme"].pk)
        target_arm = RandomizationArm.objects.get(pk=data["target_arm"].pk)
        periods = list(
            SubjectPeriod.objects.filter(subject=data["subject"]).order_by("period_no")
        )

        self.assertEqual(assignment.scheme_id, data["target_scheme"].pk)
        self.assertEqual(assignment.arm_id, target_arm.pk)
        self.assertEqual(assignment.slot_id, target_slot.pk)
        self.assertEqual(assignment.randomization_number, "NNG31-001")
        self.assertEqual(assignment.randomization_sequence, "SEQ_N_E")
        self.assertEqual(target_slot.status, "assigned")
        self.assertEqual(target_slot.assigned_subject_id, data["subject"].pk)
        self.assertTrue(source_slot.deleted)
        self.assertTrue(legacy_scheme.deleted)
        self.assertEqual(legacy_scheme.status, "closed")
        self.assertTrue(legacy_scheme.code.startswith("CROSS_OVER_NANOKINE_EPREX4000IU_deleted_"))
        self.assertEqual(target_arm.current_count, 1)
        self.assertEqual(
            [(period.treatment_code, period.kit_code) for period in periods],
            [
                ("NANOKINE", "NNG31-001"),
                ("EPREX_4000U", "R-NNG31-001"),
            ],
        )
        self.assertTrue(all(period.sequence_period.arm_id == target_arm.pk for period in periods))
        self.assertEqual(
            RandomizationEvent.objects.filter(
                subject_id=data["subject"].pk,
                event_type="Migrated",
                slot=target_slot,
            ).count(),
            1,
        )

        with patch(
            "apps.study.management.commands.reconcile_nng31_randomization_identifiers."
            "AuditContextAdapter.record_event"
        ):
            call_command(
                "reconcile_nng31_randomization_identifiers",
                study_id=data["study"].pk,
                actor_id=99,
                apply=True,
                stdout=StringIO(),
            )
        self.assertEqual(
            RandomizationEvent.objects.filter(
                subject_id=data["subject"].pk,
                event_type="Migrated",
            ).count(),
            1,
        )

    def test_rejects_legacy_assignment_when_target_treatment_sequence_differs(self):
        data = self._create_assignment_fixture(
            source_treatments=("NANOKINE", "EPREX_4000U"),
            target_treatments=("EPREX_4000U", "NANOKINE"),
        )

        with self.assertRaisesMessage(
            CommandError,
            "target NNG31-001 has ('EPREX_4000U', 'NANOKINE')",
        ):
            call_command(
                "reconcile_nng31_randomization_identifiers",
                study_id=data["study"].pk,
                actor_id=99,
                stdout=StringIO(),
            )

        data["assignment"].refresh_from_db()
        data["target_slot"].refresh_from_db()
        data["legacy_scheme"].refresh_from_db()
        self.assertEqual(data["assignment"].scheme_id, data["legacy_scheme"].pk)
        self.assertEqual(data["target_slot"].status, "available")
        self.assertFalse(data["legacy_scheme"].deleted)

    @staticmethod
    def _create_assignment_fixture(*, source_treatments, target_treatments):
        now = timezone.now()
        study = Study.objects.create(
            created_at=now,
            updated_at=now,
            code="NNG31",
            name="NNG31",
            sponsor="",
            description="",
            is_active=True,
        )
        site = Site.objects.create(
            created_at=now,
            updated_at=now,
            code="SITE01",
            name="Site 01",
            study=study,
            is_active=True,
        )
        subject = Subject.objects.create(
            created_at=now,
            updated_at=now,
            subject_code="NNG31-001",
            screening_code="NNG31-S001",
            current_sequence=1,
            enrollment_current_sequence=1,
            study=study,
            site=site,
        )
        legacy_scheme = RandomizationScheme.objects.create(
            created_at=now,
            updated_at=now,
            study=study,
            code="CROSS_OVER_NANOKINE_EPREX4000IU",
            name="Legacy crossover",
            randomization_type="stratified_blocked",
            target_randomized_total=44,
            randomization_code_prefix="NNG31-",
            randomization_code_padding=3,
            status="active",
        )
        target_scheme = RandomizationScheme.objects.create(
            created_at=now,
            updated_at=now,
            study=study,
            code="NNG31_XOVER",
            name="NNG31 crossover",
            randomization_type="blocked",
            target_randomized_total=44,
            randomization_code_prefix="NNG31-",
            randomization_code_padding=3,
            status="active",
            master_list_checksum="checksum",
        )
        source_arm = RandomizationArm.objects.create(
            created_at=now,
            updated_at=now,
            scheme=legacy_scheme,
            arm_code="SEQ_NANOKINE_EPREX4000IU",
            arm_name="NANOKINE then Eprex",
            target_count=22,
            current_count=1,
            display_order=1,
            is_active=True,
        )
        target_arm = RandomizationArm.objects.create(
            created_at=now,
            updated_at=now,
            scheme=target_scheme,
            arm_code=(
                "SEQ_N_E"
                if target_treatments == ("NANOKINE", "EPREX_4000U")
                else "SEQ_E_N"
            ),
            arm_name="Target sequence",
            target_count=22,
            current_count=0,
            display_order=1,
            is_active=True,
        )
        for period_no, treatment_code in enumerate(source_treatments, start=1):
            RandomizationSequencePeriod.objects.create(
                created_at=now,
                updated_at=now,
                scheme=legacy_scheme,
                arm=source_arm,
                period_no=period_no,
                treatment_code=treatment_code,
                display_order=period_no,
            )
        target_periods = []
        for period_no, treatment_code in enumerate(target_treatments, start=1):
            target_periods.append(
                RandomizationSequencePeriod.objects.create(
                    created_at=now,
                    updated_at=now,
                    scheme=target_scheme,
                    arm=target_arm,
                    period_no=period_no,
                    treatment_code=treatment_code,
                    display_order=period_no,
                )
            )
        source_slot = RandomizationSlot.objects.create(
            created_at=now,
            updated_at=now,
            scheme=legacy_scheme,
            arm=source_arm,
            sequence_no=1,
            status="assigned",
            assigned_subject_id=subject.pk,
            assigned_event_id=77,
            assigned_at=now,
        )
        target_slot = RandomizationSlot.objects.create(
            created_at=now,
            updated_at=now,
            scheme=target_scheme,
            arm=target_arm,
            sequence_no=1,
            randomization_code="NNG31-001",
            block_no=1,
            status="available",
        )
        assignment = SubjectRandomization.objects.create(
            created_at=now,
            updated_at=now,
            randomization_status="assigned",
            randomization_datetime=now,
            randomization_sequence=source_arm.arm_code,
            randomization_number="1",
            randomization_source="workflow_action",
            scheme=legacy_scheme,
            arm=source_arm,
            slot=source_slot,
            subject=subject,
            site=site,
            study=study,
        )
        for period_no, treatment_code in enumerate(source_treatments, start=1):
            SubjectPeriod.objects.create(
                created_at=now,
                updated_at=now,
                subject=subject,
                period_no=period_no,
                treatment_code=treatment_code,
                status="Planned",
                sequence_period=(
                    RandomizationSequencePeriod.objects.get(
                        scheme=legacy_scheme,
                        arm=source_arm,
                        period_no=period_no,
                    )
                ),
            )
        return {
            "assignment": assignment,
            "legacy_scheme": legacy_scheme,
            "source_slot": source_slot,
            "study": study,
            "subject": subject,
            "target_arm": target_arm,
            "target_periods": target_periods,
            "target_scheme": target_scheme,
            "target_slot": target_slot,
        }
