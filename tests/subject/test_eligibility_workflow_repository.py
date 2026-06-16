from django.test import TestCase
from django.utils import timezone

from apps.study.models import Site, Study
from apps.subject.infrastructure.repositories.eligibility_workflow import DjangoSubjectEligibilityWorkflowRepository
from apps.subject.models import Subject


class SubjectEligibilityWorkflowRepositoryTests(TestCase):
    def test_enrollment_initializes_subject_code_from_enrollment_sequence(self):
        study = self._create_study(code="NNG31")
        site = self._create_site(study=study)
        first_subject = self._create_subject(study=study, site=site, current_sequence=1)
        second_subject = self._create_subject(study=study, site=site, current_sequence=2)
        repository = DjangoSubjectEligibilityWorkflowRepository()

        repository.transition_enrollment_status(
            study_id=study.pk,
            site_id=site.pk,
            subject_id=first_subject.pk,
            to_status="Enrolled",
            is_enrolled=True,
            actor_user_id=7,
            source="eligibility",
            reason_code=None,
            reason_text=None,
            screen_failure_status="ScreenFailure",
            screened_status="Screened",
        )
        repository.transition_enrollment_status(
            study_id=study.pk,
            site_id=site.pk,
            subject_id=second_subject.pk,
            to_status="Enrolled",
            is_enrolled=True,
            actor_user_id=7,
            source="eligibility",
            reason_code=None,
            reason_text=None,
            screen_failure_status="ScreenFailure",
            screened_status="Screened",
        )

        first_subject.refresh_from_db()
        second_subject.refresh_from_db()
        self.assertEqual(first_subject.enrollment_current_sequence, 1)
        self.assertEqual(first_subject.subject_code, "NNG31-001")
        self.assertEqual(second_subject.enrollment_current_sequence, 2)
        self.assertEqual(second_subject.subject_code, "NNG31-002")

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
        repository = DjangoSubjectEligibilityWorkflowRepository()

        repository.transition_enrollment_status(
            study_id=study.pk,
            site_id=site.pk,
            subject_id=subject.pk,
            to_status="Enrolled",
            is_enrolled=True,
            actor_user_id=7,
            source="eligibility",
            reason_code=None,
            reason_text=None,
            screen_failure_status="ScreenFailure",
            screened_status="Screened",
        )

        subject.refresh_from_db()
        self.assertEqual(subject.enrollment_current_sequence, 10)
        self.assertEqual(subject.subject_code, "NNG31-010")

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
