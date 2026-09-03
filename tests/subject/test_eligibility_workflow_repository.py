from django.test import TestCase
from django.utils import timezone

from apps.study.models import Site, Study
from apps.subject.application.services.eligibility_workflow import (
    SubjectEligibilityWorkflowError,
    SubjectEligibilityWorkflowService,
)
from apps.subject.models import Subject, SubjectIdentifierHistory


class SubjectEligibilityWorkflowRepositoryTests(TestCase):
    def test_nng31_enrollment_assigns_subject_identifiers_separately_from_randomization(self):
        study = self._create_study(code="NNG31")
        site = self._create_site(study=study)
        first_subject = self._create_subject(study=study, site=site, current_sequence=1)
        second_subject = self._create_subject(study=study, site=site, current_sequence=2)
        service = SubjectEligibilityWorkflowService()

        service.enroll_subject(
            study_id=study.pk,
            site_id=site.pk,
            subject_id=first_subject.pk,
            actor_user_id=7,
        )
        service.enroll_subject(
            study_id=study.pk,
            site_id=site.pk,
            subject_id=second_subject.pk,
            actor_user_id=7,
        )

        first_subject.refresh_from_db()
        second_subject.refresh_from_db()
        self.assertEqual(first_subject.enrollment_current_sequence, 1)
        self.assertEqual(first_subject.subject_code, "NNG31-001")
        self.assertEqual(second_subject.enrollment_current_sequence, 2)
        self.assertEqual(second_subject.subject_code, "NNG31-002")
        self.assertEqual(
            SubjectIdentifierHistory.objects.filter(
                subject_id__in=(first_subject.pk, second_subject.pk),
                identifier_type="subject_code",
            ).count(),
            2,
        )

    def test_reenrollment_does_not_reassign_existing_subject_code(self):
        study = self._create_study(code="NNG31")
        site = self._create_site(study=study)
        subject = self._create_subject(
            study=study,
            site=site,
            current_sequence=1,
            subject_code="NNG31-010",
            enrollment_current_sequence=10,
        )
        SubjectEligibilityWorkflowService().enroll_subject(
            study_id=study.pk,
            site_id=site.pk,
            subject_id=subject.pk,
            actor_user_id=7,
        )

        subject.refresh_from_db()
        self.assertEqual(subject.enrollment_current_sequence, 10)
        self.assertEqual(subject.subject_code, "NNG31-010")

    def test_other_studies_keep_enrollment_based_subject_codes(self):
        study = self._create_study(code="ABC")
        site = self._create_site(study=study)
        subject = self._create_subject(study=study, site=site, current_sequence=1)

        SubjectEligibilityWorkflowService().enroll_subject(
            study_id=study.pk,
            site_id=site.pk,
            subject_id=subject.pk,
            actor_user_id=7,
        )

        subject.refresh_from_db()
        self.assertEqual(subject.enrollment_current_sequence, 1)
        self.assertEqual(subject.subject_code, "ABC-001")

    def test_external_subject_code_policy_blocks_enrollment_when_code_is_missing(self):
        study = self._create_study(code="EXT")
        study.subject_identifier_mode = "external"
        study.save(update_fields=["subject_identifier_mode"])
        site = self._create_site(study=study)
        subject = self._create_subject(study=study, site=site, current_sequence=1)

        with self.assertRaisesMessage(
            SubjectEligibilityWorkflowError,
            "must be assigned before enrollment",
        ):
            SubjectEligibilityWorkflowService().enroll_subject(
                study_id=study.pk,
                site_id=site.pk,
                subject_id=subject.pk,
                actor_user_id=7,
            )

        self.assertFalse(hasattr(subject, "enrollment"))

    @staticmethod
    def _create_study(*, code: str):
        now = timezone.now()
        return Study.objects.create(
            code=code,
            name=code,
            sponsor="",
            description="",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def _create_site(*, study):
        now = timezone.now()
        return Site.objects.create(
            code="SITE-01",
            name="Site 01",
            study=study,
            is_active=True,
            deleted=False,
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def _create_subject(
        *,
        study,
        site,
        current_sequence: int,
        subject_code: str | None = None,
        enrollment_current_sequence: int | None = None,
    ):
        now = timezone.now()
        return Subject.objects.create(
            subject_code=subject_code,
            screening_code=f"{study.code}-S{str(current_sequence).rjust(3, '0')}",
            current_sequence=current_sequence,
            enrollment_current_sequence=enrollment_current_sequence,
            study=study,
            site=site,
            deleted=False,
            created_at=now,
            updated_at=now,
        )
