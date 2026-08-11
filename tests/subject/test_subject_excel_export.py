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
        "event_name": "Screening",
        "crf_code": "DEMOGRAPHICS",
        "crf_name": "Demographics",
        "field_key": "AGE",
        "field_label": "Age",
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
                "Subject Code",
                "Screening Code",
                "Randomization Code",
                "Visit",
                "Age",
            ],
        )
        self.assertEqual(
            list(worksheet.values)[1:],
            [
                ("SUB-001", "SCR-001", "RND-001", "Visit 1", "42"),
                ("SUB-002", "SCR-002", "RND-002", "Visit 1", "=unsafe"),
            ],
        )
        self.assertEqual(worksheet["E3"].data_type, "s")
        self.assertEqual(worksheet.freeze_panes, "A2")
        self.assertEqual(result.subject_count, 2)
        self.assertEqual(result.field_count, 1)
        self.assertEqual(data_adapter.calls[0]["subject_ids"], (100, 101))

    def test_disambiguates_duplicate_field_descriptions_with_readable_context(self):
        selected_fields = (
            {
                **self.field,
                "token": "30:40",
                "field_label": "Visit Date",
            },
            {
                **self.field,
                "token": "31:41",
                "binding_id": 31,
                "field_template_id": 41,
                "event_code": "BASELINE",
                "event_name": "Baseline",
                "crf_code": "VITALS",
                "crf_name": "Vital Signs",
                "field_key": "VISIT_DATE",
                "field_label": "Visit Date",
                "header": "BASELINE.VITALS.VISIT_DATE",
            },
        )

        content = SubjectExcelExportService._build_workbook(
            subject_rows=(
                {
                    "id": 100,
                    "subject_code": "SUB-001",
                    "screening_code": "SCR-001",
                    "randomization_code": "RND-001",
                },
            ),
            selected_fields=selected_fields,
            values_by_subject_id={
                100: {
                    "30:40": "2026-08-01",
                    "31:41": "2026-08-02",
                }
            },
        )

        worksheet = load_workbook(BytesIO(content))["Subjects"]
        self.assertEqual(
            [cell.value for cell in worksheet[1]][-2:],
            [
                "Visit",
                "Visit Date",
            ],
        )

    def test_exports_each_repeated_form_instance_on_its_own_row(self):
        repeated_fields = (
            {
                **self.field,
                "token": "31:41",
                "binding_id": 31,
                "field_template_id": 41,
                "field_key": "AETERM",
                "field_label": "Adverse Event Term",
            },
            {
                **self.field,
                "token": "31:42",
                "binding_id": 31,
                "field_template_id": 42,
                "field_key": "AESTDTC",
                "field_label": "AE Start Date",
            },
        )

        content = SubjectExcelExportService._build_workbook(
            subject_rows=(
                {
                    "id": 100,
                    "subject_code": "NNG31-002",
                    "screening_code": "NNG31-S001",
                    "randomization_code": "2",
                },
            ),
            selected_fields=repeated_fields,
            values_by_subject_id={
                100: {
                    "31:41": "Sốt; Đau đầu",
                    "31:42": "2026-06-18; 2026-06-15",
                }
            },
        )

        worksheet = load_workbook(BytesIO(content))["Subjects"]
        self.assertEqual(
            list(worksheet.values)[1:],
            [
                (
                    "NNG31-002",
                    "NNG31-S001",
                    "2",
                    "Visit 1",
                    "Sốt; Đau đầu",
                    "2026-06-18; 2026-06-15",
                ),
            ],
        )

    def test_exports_semantic_visit_labels(self):
        content = SubjectExcelExportService._build_workbook(
            subject_rows=(
                {
                    "id": 100,
                    "subject_code": "SUB-001",
                    "screening_code": "SCR-001",
                    "randomization_code": "RND-001",
                },
            ),
            selected_fields=(self.field,),
            values_by_subject_id={
                100: (
                    {
                        "30:40": "Screening",
                        "__export_visit_sort_key__": (
                            0, 0, 11, 1, 11, "Screening", None,
                        ),
                    },
                    {
                        "30:40": "Visit 1",
                        "__export_visit_sort_key__": (
                            1, 0, 21, 1, 21, "Visit 1", None,
                        ),
                    },
                    {
                        "30:40": "FU 1 #1",
                        "__export_visit_sort_key__": (
                            2, 1, 31, 1, 31, "FU 1", 1,
                        ),
                    },
                    {
                        "30:40": "FU 1 #2",
                        "__export_visit_sort_key__": (
                            2, 2, 41, 2, 41, "FU 1", 2,
                        ),
                    },
                )
            },
        )

        worksheet = load_workbook(BytesIO(content))["Subjects"]
        self.assertEqual(
            [row[3] for row in list(worksheet.values)[1:]],
            [
                "Screening",
                "Visit 1",
                "FU 1 #1",
                "FU 1 #2",
            ],
        )
        self.assertEqual(
            [row[4] for row in list(worksheet.values)[1:]],
            [
                "Screening",
                "Visit 1",
                "FU 1 #1",
                "FU 1 #2",
            ],
        )

    def test_falls_back_to_technical_header_without_field_description(self):
        field_without_description = {
            **self.field,
            "field_label": "",
        }

        self.assertEqual(
            SubjectExcelExportService._field_description_headers(
                (field_without_description,),
            ),
            ("SCREENING.DEMOGRAPHICS.AGE",),
        )

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
