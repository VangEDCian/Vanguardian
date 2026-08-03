from io import BytesIO

from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from openpyxl import load_workbook

from apps.study.models import Site, Study
from apps.subject.application.services.excel_export import (
    SubjectExcelExportSelectionError,
    SubjectExcelExportService,
)
from apps.subject.infrastructure.repositories.subject_excel_export import (
    DjangoSubjectExcelExportRepository,
)
from apps.subject.models import Subject


class SubjectExcelExportServiceTests(SimpleTestCase):
    field = {
        "token": "30:40",
        "binding_id": 30,
        "event_definition_id": 10,
        "crf_template_id": 20,
        "field_template_id": 40,
        "event_code": "SCREENING",
        "crf_code": "DEMOGRAPHICS",
        "field_key": "AGE",
        "header": "SCREENING.DEMOGRAPHICS.AGE",
    }

    def test_exports_one_flat_row_per_scoped_subject(self):
        repository = _SubjectRepositoryStub(
            rows=(
                {
                    "id": 100,
                    "subject_code": "SUB-001",
                    "screening_code": "SCR-001",
                    "randomization_code": "RND-001",
                },
                {
                    "id": 101,
                    "subject_code": "SUB-002",
                    "screening_code": "SCR-002",
                    "randomization_code": "RND-002",
                },
            )
        )
        data_adapter = _DataAdapterStub(
            values={
                100: {"30:40": "42"},
                101: {"30:40": "=unsafe"},
            }
        )
        service = SubjectExcelExportService(
            repository=repository,
            field_catalog_adapter=_CatalogAdapterStub(field=self.field),
            data_capture_adapter=data_adapter,
        )

        result = service.export(
            study_id=1,
            site_id=2,
            subject_ids=(100, 101, 999),
            selected_field_tokens=("30:40",),
        )

        workbook = load_workbook(BytesIO(result.content), data_only=False)
        worksheet = workbook["Subjects"]
        self.assertEqual(
            [cell.value for cell in worksheet[1]],
            [
                "subject_id",
                "subject_code",
                "screening_code",
                "randomization_code",
                "SCREENING.DEMOGRAPHICS.AGE",
            ],
        )
        self.assertEqual(
            list(worksheet.values)[1:],
            [
                (100, "SUB-001", "SCR-001", "RND-001", "42"),
                (101, "SUB-002", "SCR-002", "RND-002", "=unsafe"),
            ],
        )
        self.assertEqual(worksheet["E3"].data_type, "s")
        self.assertEqual(worksheet.freeze_panes, "A2")
        self.assertEqual(result.subject_count, 2)
        self.assertEqual(result.field_count, 1)
        self.assertEqual(data_adapter.calls[0]["subject_ids"], (100, 101))

    def test_rejects_field_token_not_in_current_study_catalog(self):
        service = SubjectExcelExportService(
            repository=_SubjectRepositoryStub(rows=()),
            field_catalog_adapter=_CatalogAdapterStub(field=self.field),
            data_capture_adapter=_DataAdapterStub(values={}),
        )

        with self.assertRaisesMessage(
            SubjectExcelExportSelectionError,
            "invalid",
        ):
            service.export(
                study_id=1,
                site_id=2,
                subject_ids=(100,),
                selected_field_tokens=("99:99",),
            )


class SubjectExcelExportRepositoryTests(TestCase):
    def test_lists_only_subjects_in_the_authorized_study_site(self):
        now = timezone.now()
        study = Study.objects.create(
            code="EXPORT-STUDY",
            name="Export Study",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        other_study = Study.objects.create(
            code="EXPORT-OTHER",
            name="Other Export Study",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        site = self._create_site(study, "EXPORT-SITE")
        other_site = self._create_site(study, "EXPORT-OTHER-SITE")
        other_study_site = self._create_site(
            other_study,
            "EXPORT-OTHER-STUDY-SITE",
        )
        subject = self._create_subject(study, site, 1)
        other_site_subject = self._create_subject(study, other_site, 2)
        other_study_subject = self._create_subject(
            other_study,
            other_study_site,
            1,
        )

        rows = DjangoSubjectExcelExportRepository().list_scoped_subject_rows(
            study_id=study.pk,
            site_id=site.pk,
            subject_ids=(
                subject.pk,
                other_site_subject.pk,
                other_study_subject.pk,
            ),
        )

        self.assertEqual(tuple(row["id"] for row in rows), (subject.pk,))

    @staticmethod
    def _create_site(study, code):
        now = timezone.now()
        return Site.objects.create(
            study=study,
            code=code,
            name=code,
            is_active=True,
            deleted=False,
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def _create_subject(study, site, sequence):
        now = timezone.now()
        return Subject.objects.create(
            screening_code=f"{study.code}-SCR-{sequence}",
            current_sequence=sequence,
            study=study,
            site=site,
            deleted=False,
            created_at=now,
            updated_at=now,
        )


class _SubjectRepositoryStub:
    def __init__(self, *, rows):
        self.rows = rows

    def list_scoped_subject_rows(self, **kwargs):
        self.call = kwargs
        return self.rows


class _CatalogAdapterStub:
    def __init__(self, *, field):
        self.field = field

    def list_groups(self, *, study_id):
        self.study_id = study_id
        return [{"forms": [{"fields": [self.field]}]}]


class _DataAdapterStub:
    def __init__(self, *, values):
        self.values = values
        self.calls = []

    def read_values(self, **kwargs):
        self.calls.append(kwargs)
        return self.values
