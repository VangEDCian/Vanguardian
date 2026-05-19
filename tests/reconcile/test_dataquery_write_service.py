from django.test import SimpleTestCase

from apps.reconcile.application import ReconcileDataQueryWriteService
from apps.reconcile.models import ReconcileQueryThreadSourceChoices


class ReconcileDataQueryWriteServiceTests(SimpleTestCase):
    def test_add_update_value_threads_for_changed_fields_creates_system_thread_for_open_queries(self):
        repository = _ReconcileRepositoryStub()

        created_count = ReconcileDataQueryWriteService(repository=repository).add_update_value_threads_for_changed_fields(
            page_state_id=11,
            crf_template_id=31,
            values_by_field_key={
                "field_1": "Y",
                "field_2": "A,B",
                "field_3": "raw value",
                "missing": "ignored",
            },
            actor_user_id=99,
        )

        self.assertEqual(created_count, 3)
        self.assertEqual(
            repository.created_threads,
            [
                {
                    "dataquery_id": 101,
                    "message_text": "update value to Yes",
                    "message_type": "comment",
                    "actor_user_id": 99,
                    "source": ReconcileQueryThreadSourceChoices.SYSTEM,
                },
                {
                    "dataquery_id": 102,
                    "message_text": "update value to Alpha, Beta",
                    "message_type": "comment",
                    "actor_user_id": 99,
                    "source": ReconcileQueryThreadSourceChoices.SYSTEM,
                },
                {
                    "dataquery_id": 103,
                    "message_text": "update value to raw value",
                    "message_type": "comment",
                    "actor_user_id": 99,
                    "source": ReconcileQueryThreadSourceChoices.SYSTEM,
                }
            ],
        )


class _ReconcileRepositoryStub:
    def __init__(self):
        self.created_threads = []

    def list_field_key_to_id(self, *, crf_template_id):
        return {"field_1": 1, "field_2": 2, "field_3": 3}

    def list_latest_open_query_ids_by_page_state_and_field_templates(self, *, page_state_id, field_template_ids):
        self.page_state_id = page_state_id
        self.field_template_ids = field_template_ids
        return {1: 101, 2: 102, 3: 103}

    def list_field_thread_value_contexts(self, *, crf_template_id, field_template_ids):
        return {
            1: {
                "control_type": "radio",
                "options": '{"source":"static","static":[{"label":"Yes","value":"Y"},{"label":"No","value":"N"}]}',
            },
            2: {
                "control_type": "checkbox",
                "options": {
                    "source": "static",
                    "static": [
                        {"label": "Alpha", "value": "A"},
                        {"label": "Beta", "value": "B"},
                    ],
                },
            },
            3: {
                "control_type": "text",
                "options": '{"source":"lookup","static":[{"label":"Ignored","value":"raw value"}]}',
            },
        }

    def create_query_thread_message(self, **kwargs):
        self.created_threads.append(
            {
                "dataquery_id": kwargs["dataquery_id"],
                "message_text": kwargs["message_text"],
                "message_type": kwargs["message_type"],
                "actor_user_id": kwargs["actor_user_id"],
                "source": kwargs["source"],
            }
        )
