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
            is_repeatable_within_event=True,
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
                    "control_type": "RADIO",
                    "choice_labels": {"1": "Adult", "0": "Child"},
                },
            )
        )

        groups = SubjectExportFieldCatalogService(
            repository=repository,
            crf_context_adapter=crf_adapter,
        ).list_groups(study_id=1)

        self.assertEqual(repository.list_calls, [(1, "v2.0")])
        self.assertEqual(crf_adapter.template_id_batches, [(20,)])
        self.assertEqual(groups[0]["event_code"], "SCREENING")
        field = groups[0]["forms"][0]["fields"][0]
        self.assertEqual(field["token"], "30:40")
        self.assertEqual(field["header"], "SCREENING.DEMOGRAPHICS.AGE")
        self.assertEqual(field["field_label"], "Age")
        self.assertTrue(field["is_repeatable_within_event"])
        self.assertEqual(field["control_type"], "RADIO")
        self.assertEqual(field["choice_labels"], {"1": "Adult", "0": "Child"})

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

    def test_loads_fields_for_all_bound_forms_in_one_batch(self):
        event = SimpleNamespace(pk=10, code="SCREENING", name="Screening")
        bindings = tuple(
            SimpleNamespace(
                pk=30 + index,
                event_definition=event,
                form_definition=SimpleNamespace(
                    pk=20 + index,
                    code=f"FORM_{index}",
                    name=f"Form {index}",
                ),
                is_repeatable_within_event=False,
            )
            for index in range(2)
        )
        crf_adapter = _CrfAdapterStub(
            fields_by_template_id={
                20: ({"id": "40", "field_key": "AGE", "label": "Age"},),
                21: ({"id": "41", "field_key": "SEX", "label": "Sex"},),
            }
        )

        groups = SubjectExportFieldCatalogService(
            repository=_CatalogRepositoryStub(
                study_version="v2.0",
                bindings=bindings,
            ),
            crf_context_adapter=crf_adapter,
        ).list_groups(study_id=1)

        self.assertEqual(crf_adapter.template_id_batches, [(20, 21)])
        self.assertEqual(len(groups[0]["forms"]), 2)


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
    def __init__(self, *, fields=(), fields_by_template_id=None):
        self.fields = fields
        self.fields_by_template_id = fields_by_template_id
        self.template_id_batches = []

    def list_export_fields_by_template_ids(self, *, template_ids, language_code=None):
        normalized_template_ids = tuple(sorted(template_ids))
        self.template_id_batches.append(normalized_template_ids)
        if self.fields_by_template_id is not None:
            return self.fields_by_template_id
        return {
            template_id: self.fields
            for template_id in normalized_template_ids
        }
