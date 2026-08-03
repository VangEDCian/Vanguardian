from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.study.application.services.subject_export import (
    SubjectExportFieldCatalogService,
)


class SubjectExportFieldCatalogServiceTests(SimpleTestCase):
    def test_groups_active_version_fields_by_event_definition(self):
        event = SimpleNamespace(pk=10, code="SCREENING", name="Screening")
        form = SimpleNamespace(
            pk=20,
            code="DEMOGRAPHICS",
            name="Demographics",
        )
        binding = SimpleNamespace(
            pk=30,
            event_definition=event,
            form_definition=form,
        )
        repository = _CatalogRepositoryStub(
            study_version="v2.0",
            bindings=(binding,),
        )
        crf_adapter = _CrfAdapterStub(
            fields=(
                {
                    "id": "40",
                    "field_key": "AGE",
                    "label": "Age",
                },
            )
        )

        groups = SubjectExportFieldCatalogService(
            repository=repository,
            crf_context_adapter=crf_adapter,
        ).list_groups(study_id=1)

        self.assertEqual(repository.list_calls, [(1, "v2.0")])
        self.assertEqual(crf_adapter.template_ids, [20])
        self.assertEqual(groups[0]["event_code"], "SCREENING")
        field = groups[0]["forms"][0]["fields"][0]
        self.assertEqual(field["token"], "30:40")
        self.assertEqual(field["header"], "SCREENING.DEMOGRAPHICS.AGE")
        self.assertEqual(field["field_label"], "Age")

    def test_returns_no_groups_when_study_has_no_active_version(self):
        repository = _CatalogRepositoryStub(
            study_version=None,
            bindings=(),
        )

        groups = SubjectExportFieldCatalogService(
            repository=repository,
            crf_context_adapter=_CrfAdapterStub(fields=()),
        ).list_groups(study_id=1)

        self.assertEqual(groups, [])
        self.assertEqual(repository.list_calls, [])


class _CatalogRepositoryStub:
    def __init__(self, *, study_version, bindings):
        self.study_version = study_version
        self.bindings = bindings
        self.list_calls = []

    def resolve_active_study_version(self, *, study_id):
        self.study_id = study_id
        return self.study_version

    def list_enabled_bindings(self, *, study_id, study_version):
        self.list_calls.append((study_id, study_version))
        return self.bindings


class _CrfAdapterStub:
    def __init__(self, *, fields):
        self.fields = fields
        self.template_ids = []

    def list_template_fields_with_ui_config(self, *, template_id):
        self.template_ids.append(template_id)
        return self.fields
