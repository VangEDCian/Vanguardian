from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase

from apps.crf.application.commands import (
    CrfTemplateCommandService,
    UpsertCrfTemplateCommand,
)
from apps.crf.application.form_builder_orchestration import (
    FormBuilderOrchestrationService,
    SaveFieldAggregateCommand,
)
from apps.crf.domain.aggregate import FieldTemplateAggregate
from apps.crf.domain.exceptions import FormBuilderDomainValidationError
from apps.crf.infrastructure.repositories.form_builder import DjangoOrmFormBuilderRepository
from apps.study.presentation.web.tables import CrfTemplateListTable


class CrfTemplateListTableTests(SimpleTestCase):
    def test_render_actions_contains_detail_and_builder_links(self):
        record = SimpleNamespace(pk=17)

        html = CrfTemplateListTable.render_actions(record)

        self.assertIn('/crf/forms/17', html)
        self.assertIn('/crf/forms/17/builder', html)
        self.assertIn('Detail', html)
        self.assertIn('Builder', html)


class CrfTemplateCommandServiceTests(SimpleTestCase):
    @patch.object(CrfTemplateCommandService, "_resolve_selected_study_id", return_value=5)
    def test_upsert_crf_template_sets_bilingual_name_translations(self, _mock_selected_study):
        template_instance = MagicMock()
        template_model = MagicMock()
        template_model.objects.filter.return_value.first.return_value = None
        template_model.return_value = template_instance

        service = CrfTemplateCommandService()
        service.template_model = template_model

        request = SimpleNamespace(
            user=SimpleNamespace(is_authenticated=True, is_superuser=True),
            COOKIES={"study_dropdown": "5"},
        )

        outcome = CrfTemplateCommandService.upsert_crf_template.__wrapped__(
            service,
            UpsertCrfTemplateCommand(
                study_id=5,
                code="AE",
                version="v1.0",
                vi_name="Bien co bat loi",
                en_name="Adverse Event",
                actor_user_id=9,
            ),
            request=request,
            now="2026-04-24T10:00:00",
        )

        self.assertEqual(outcome, "created")
        template_instance.set_current_language.assert_any_call("vi", initialize=True)
        template_instance.set_current_language.assert_any_call("en", initialize=True)
        self.assertEqual(template_instance.name, "Adverse Event")
        template_instance.save.assert_called_once()


class FieldTemplateAggregateTests(SimpleTestCase):
    def test_rejects_duplicate_field_key_within_same_form(self):
        with self.assertRaises(FormBuilderDomainValidationError):
            FieldTemplateAggregate.from_payload(
                field_key="VISIT_DATE",
                data_type="DATE",
                is_active=True,
                display_order=1,
                section_template_id=3,
                label_en="Visit Date",
                label_vi="Ngay tham kham",
                definition={
                    "sdtm": {"domain": "SV", "variable": "SVSTDTC", "role": "Topic"},
                    "unit": "",
                    "range_min": "",
                    "range_max": "",
                    "precision": "",
                    "allowed_missing_values": "",
                    "codelist": "",
                    "data_semantic": "",
                    "comments": "",
                    "text_max_length": "",
                    "text_min_length": "",
                    "pattern": "",
                    "pattern_err_msg": "",
                },
                ui_config={
                    "control_type": "date_picker",
                    "layout": "",
                    "text": "",
                    "behavior": "",
                    "options": "",
                    "style": "",
                },
                validation_rules=[
                    {
                        "rule_type": "custom",
                        "expression": "$val != ''",
                        "severity": "error",
                        "mode": "blocking",
                        "messages": {"en": "Required", "vi": "Bat buoc"},
                    }
                ],
                field_keys_in_form=("visit_date",),
            )


class FormBuilderOrchestrationServiceTests(SimpleTestCase):
    @patch.object(FormBuilderOrchestrationService, "_resolve_selected_study_id", return_value=3)
    def test_save_field_records_audit_log_for_created_field(self, _mock_selected_study):
        repository = MagicMock()
        audit_service = MagicMock()
        field = SimpleNamespace(
            pk=21,
            field_key="VISIT_DATE",
            data_type="DATE",
            is_active=True,
            display_order=1,
        )

        repository.get_form_by_scope.return_value = SimpleNamespace(pk=7)
        repository.list_field_keys_for_form.return_value = ()
        repository.save_field_aggregate.return_value = ("created", field)

        service = FormBuilderOrchestrationService(
            repository=repository,
            audit_service=audit_service,
        )

        request = SimpleNamespace(
            user=SimpleNamespace(is_authenticated=True, is_superuser=True),
            COOKIES={"study_dropdown": "3"},
        )
        command = SaveFieldAggregateCommand(
            study_id=3,
            form_id=7,
            actor_user_id=11,
            field_id=None,
            field_key="VISIT_DATE",
            data_type="DATE",
            is_active=True,
            display_order=1,
            section_template_id=4,
            label_en="Visit Date",
            label_vi="Ngay tham kham",
            definition={
                "sdtm": {"domain": "SV", "variable": "SVSTDTC", "role": "Topic"},
                "unit": "",
                "range_min": "",
                "range_max": "",
                "precision": "",
                "allowed_missing_values": "",
                "codelist": "",
                "data_semantic": "",
                "comments": "",
                "text_max_length": "",
                "text_min_length": "",
                "pattern": "",
                "pattern_err_msg": "",
            },
            ui_config={
                "control_type": "date_picker",
                "layout": "",
                "text": "",
                "behavior": "",
                "options": "",
                "style": "",
            },
            validation_rules=[
                {
                    "rule_type": "custom",
                    "expression": "$val != ''",
                    "severity": "error",
                    "mode": "blocking",
                    "messages": {"en": "Required"},
                }
            ],
        )

        result = FormBuilderOrchestrationService.save_field.__wrapped__(
            service,
            request=request,
            command=command,
        )

        self.assertEqual(result, {"action": "created", "field_id": 21})
        audit_service.record_field_created.assert_called_once()


class DjangoOrmFormBuilderRepositoryTests(SimpleTestCase):
    def test_apply_field_snapshot_sets_bilingual_field_labels(self):
        repository = DjangoOrmFormBuilderRepository()
        field = MagicMock()

        repository._apply_field_snapshot(
            field,
            {
                "field_key": "AE_TERM",
                "data_type": "TEXT",
                "is_active": True,
                "display_order": 2,
                "section_template_id": 7,
                "label_en": "Adverse Event Term",
                "label_vi": "Thuat ngu bien co bat loi",
            },
            now="2026-04-24T11:00:00",
            actor_user_id=8,
        )

        self.assertEqual(field.field_key, "AE_TERM")
        self.assertEqual(field.data_type, "TEXT")
        field.set_current_language.assert_any_call("en", initialize=True)
        field.set_current_language.assert_any_call("vi", initialize=True)
        self.assertEqual(field.label, "Thuat ngu bien co bat loi")

    @patch("apps.crf.infrastructure.repositories.form_builder.CrfFieldValidationRule")
    def test_replace_validation_rules_persists_translated_messages(self, mock_rule_cls):
        existing_rule = MagicMock()
        mock_rule_cls.objects.filter.return_value.prefetch_related.return_value = [existing_rule]

        created_rule = MagicMock()
        mock_rule_cls.return_value = created_rule

        repository = DjangoOrmFormBuilderRepository()
        snapshots = [
            {
                "rule_type": "custom",
                "expression": "$val != ''",
                "severity": "error",
                "mode": "blocking",
                "translations": [
                    {"language_code": "en", "message": "Required"},
                    {"language_code": "vi", "message": "Bat buoc"},
                ],
            }
        ]

        rules = repository._replace_validation_rules(
            field_template_id=12,
            snapshots=snapshots,
            actor_user_id=5,
            now="2026-04-24T12:00:00",
        )

        existing_rule.delete.assert_called_once()
        created_rule.set_current_language.assert_any_call("en", initialize=True)
        created_rule.set_current_language.assert_any_call("vi", initialize=True)
        self.assertEqual(created_rule.message, "Bat buoc")
        self.assertEqual(rules, [created_rule])


class CrfFormBuilderViewValidationTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_duplicate_field_key_error_is_bound_to_field_key(self):
        from apps.crf.presentation.web.forms import CrfFieldCreateForm
        from apps.crf.presentation.web.views import CrfFormBuilderView

        form = CrfFieldCreateForm()
        form.cleaned_data = {}

        CrfFormBuilderView._bind_field_domain_error(
            form,
            FormBuilderDomainValidationError("field_key must be unique in form scope."),
        )

        self.assertIn("field_key", form.errors)
        self.assertIn("Field Key", form.errors["field_key"][0])
