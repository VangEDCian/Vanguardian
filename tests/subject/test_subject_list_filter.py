from django.test import TestCase
from django.utils import timezone

from apps.study.models import Site, Study
from apps.subject.models import Subject, SubjectEnrollment, SubjectRandomization
from apps.subject.presentation.web.forms import SubjectsToolbarForm


class SubjectsToolbarFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        now = timezone.now()
        cls.study = Study.objects.create(
            code="FILTER-STUDY",
            name="Filter Study",
            sponsor="",
            description="",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        cls.site = Site.objects.create(
            code="FILTER-SITE",
            name="Filter Site",
            study=cls.study,
            is_active=True,
            deleted=False,
            created_at=now,
            updated_at=now,
        )

        cls.screening_subject = cls._create_subject(sequence=1)
        cls.eligible_subject = cls._create_subject(sequence=2)
        cls.fail_eligible_subject = cls._create_subject(sequence=3)
        cls.enrolled_only_subject = cls._create_subject(sequence=4)
        cls.randomized_enrolled_subject = cls._create_subject(sequence=5)

        cls._create_enrollment(cls.eligible_subject, status="Eligible", is_enrolled=False)
        cls._create_enrollment(
            cls.fail_eligible_subject,
            status="ScreenFailure",
            is_enrolled=False,
        )
        cls._create_enrollment(cls.enrolled_only_subject, status="Enrolled", is_enrolled=True)
        cls._create_enrollment(
            cls.randomized_enrolled_subject,
            status="Enrolled",
            is_enrolled=True,
        )
        SubjectRandomization.objects.create(
            subject=cls.randomized_enrolled_subject,
            study=cls.study,
            site=cls.site,
            randomization_status="assigned",
            randomization_number="NNG31-001",
            deleted=False,
            created_at=now,
            updated_at=now,
        )

    def test_defaults_to_all_and_renders_requested_options(self):
        filterset = SubjectsToolbarForm(queryset=Subject.objects.all())

        self.assertEqual(
            list(filterset.form.fields),
            ["subject_status", "total", "search"],
        )
        self.assertEqual(
            list(filterset.form.fields["subject_status"].choices),
            [
                ("", "All"),
                ("randomized_enrolled", "Randomized & Enrolled"),
                ("screening", "Screening"),
                ("fail_eligible", "Fail Eligible"),
            ],
        )
        self.assertEqual(
            set(filterset.qs.values_list("pk", flat=True)),
            {
                self.screening_subject.pk,
                self.eligible_subject.pk,
                self.fail_eligible_subject.pk,
                self.enrolled_only_subject.pk,
                self.randomized_enrolled_subject.pk,
            },
        )

    def test_filters_randomized_and_enrolled_subjects(self):
        self.assertEqual(
            self._filtered_subject_ids("randomized_enrolled"),
            {self.randomized_enrolled_subject.pk},
        )

    def test_filters_screening_subjects(self):
        self.assertEqual(
            self._filtered_subject_ids("screening"),
            {self.screening_subject.pk, self.eligible_subject.pk},
        )

    def test_filters_fail_eligible_subjects(self):
        self.assertEqual(
            self._filtered_subject_ids("fail_eligible"),
            {self.fail_eligible_subject.pk},
        )

    def _filtered_subject_ids(self, status):
        return set(
            SubjectsToolbarForm(
                {"subject_status": status},
                queryset=Subject.objects.all(),
            ).qs.values_list("pk", flat=True)
        )

    @classmethod
    def _create_subject(cls, *, sequence):
        now = timezone.now()
        return Subject.objects.create(
            screening_code=f"FILTER-S{sequence:03d}",
            current_sequence=sequence,
            study=cls.study,
            site=cls.site,
            deleted=False,
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def _create_enrollment(cls, subject, *, status, is_enrolled):
        now = timezone.now()
        return SubjectEnrollment.objects.create(
            subject=subject,
            study=cls.study,
            site=cls.site,
            status=status,
            is_enrolled=is_enrolled,
            deleted=False,
            created_at=now,
            updated_at=now,
        )
