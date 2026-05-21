from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.reconcile.application import ReconcileDataQueryWriteService
from apps.reconcile.infrastructure.repositories.dataquery_write import DjangoReconcileDataQueryWriteRepository
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
                    "message_text": "Update value to **Yes**",
                    "message_type": "comment",
                    "actor_user_id": 99,
                    "source": ReconcileQueryThreadSourceChoices.SYSTEM,
                },
                {
                    "dataquery_id": 102,
                    "message_text": "Update value to **Alpha, Beta**",
                    "message_type": "comment",
                    "actor_user_id": 99,
                    "source": ReconcileQueryThreadSourceChoices.SYSTEM,
                },
                {
                    "dataquery_id": 103,
                    "message_text": "Update value to **raw value**",
                    "message_type": "comment",
                    "actor_user_id": 99,
                    "source": ReconcileQueryThreadSourceChoices.SYSTEM,
                }
            ],
        )

    def test_reply_to_query_marks_query_answered_by_reply_actor(self):
        repository = _ReplyRepositoryStub()

        result = ReconcileDataQueryWriteService(repository=repository).reply_to_query(
            dataquery_id=101,
            page_state_id=23,
            field_template_id=11,
            message_text="Answered by site",
            actor_user_id=7,
        )

        self.assertEqual(result["dataquery_id"], 101)
        self.assertEqual(repository.answered_calls[0]["dataquery_id"], 101)
        self.assertEqual(repository.answered_calls[0]["page_state_id"], 23)
        self.assertEqual(repository.answered_calls[0]["field_template_id"], 11)
        self.assertEqual(repository.answered_calls[0]["actor_user_id"], 7)
        self.assertIs(repository.answered_calls[0]["now"], repository.created_threads[0]["now"])

    def test_reply_to_query_rejects_non_participant(self):
        repository = _ReplyRepositoryStub(can_respond=False)

        with self.assertRaisesMessage(ValueError, "Only the query opener or assignee can respond to this query."):
            ReconcileDataQueryWriteService(repository=repository).reply_to_query(
                dataquery_id=101,
                page_state_id=23,
                field_template_id=11,
                message_text="Answered by site",
                actor_user_id=99,
            )

        self.assertEqual(repository.created_threads, [])
        self.assertEqual(repository.answered_calls, [])

    def test_reply_and_close_query_requires_resolved_flag(self):
        repository = _ReplyRepositoryStub()

        with self.assertRaisesMessage(ValueError, "Query must be resolved before it can be closed."):
            ReconcileDataQueryWriteService(repository=repository).reply_and_close_query(
                dataquery_id=101,
                page_state_id=23,
                field_template_id=11,
                message_text="Close it",
                actor_user_id=7,
                is_resolved=False,
            )

        self.assertEqual(repository.created_threads, [])
        self.assertEqual(repository.closed_calls, [])

    def test_reply_and_close_query_closes_when_resolved(self):
        repository = _ReplyRepositoryStub()

        result = ReconcileDataQueryWriteService(repository=repository).reply_and_close_query(
            dataquery_id=101,
            page_state_id=23,
            field_template_id=11,
            message_text="Close it",
            actor_user_id=7,
            is_resolved=True,
        )

        self.assertIs(result["closed"], True)
        self.assertEqual(repository.closed_calls[0]["is_resolved"], True)
        self.assertIs(repository.closed_calls[0]["now"], repository.created_threads[0]["now"])

    def test_cancel_query_marks_query_cancelled(self):
        repository = _ReplyRepositoryStub()

        result = ReconcileDataQueryWriteService(repository=repository).cancel_query(
            dataquery_id=101,
            page_state_id=23,
            field_template_id=11,
            actor_user_id=7,
        )

        self.assertIs(result["cancelled"], True)
        self.assertEqual(repository.cancelled_calls[0]["dataquery_id"], 101)
        self.assertEqual(repository.cancelled_calls[0]["page_state_id"], 23)
        self.assertEqual(repository.cancelled_calls[0]["field_template_id"], 11)
        self.assertEqual(repository.cancelled_calls[0]["actor_user_id"], 7)


class ReconcileDataQueryWriteRepositoryTests(SimpleTestCase):
    def test_create_manual_open_query_persists_current_page_entry_field_context(self):
        repository = _ReconcileRepositoryWithEntryContext()

        with patch(
            "apps.reconcile.infrastructure.repositories.dataquery_write.ReconcileDataQuery.objects.create",
            return_value=SimpleNamespace(pk=501),
        ) as create_dataquery:
            dataquery = repository.create_manual_open_query(
                page_state_id=23,
                field_template_id=11,
                question_text="Please review",
                actor_user_id=7,
                now="now",
            )

        self.assertEqual(dataquery.pk, 501)
        created = create_dataquery.call_args.kwargs
        self.assertEqual(created["page_entry_id"], 301)
        self.assertEqual(created["field_template_id"], 11)
        self.assertEqual(created["value_snapshot"], "1")
        self.assertEqual(created["field_path"], "$.CONTRACEPT_YN")
        self.assertEqual(created["data_version"], "v2")
        self.assertEqual(created["assigned_to_id"], 42)

    def test_entry_field_value_snapshot_uses_field_id_fallback_and_jsonpath_bracket_notation(self):
        snapshot, storage_key = DjangoReconcileDataQueryWriteRepository._entry_field_value_snapshot(
            payload={"field_12": ["A", "B"]},
            field_key="field key with space",
            field_template_id=12,
        )

        self.assertEqual(snapshot, '["A", "B"]')
        self.assertEqual(storage_key, "field_12")
        self.assertEqual(
            DjangoReconcileDataQueryWriteRepository._jsonpath_for_field_key("field key with space"),
            '$["field key with space"]',
        )

    def test_entry_field_value_snapshot_uses_field_key_for_jsonpath_evaluator(self):
        snapshot, storage_key = DjangoReconcileDataQueryWriteRepository._entry_field_value_snapshot(
            payload={"CONTRACEPT_YN": "1", "PREGPLAN_YN": "0"},
            field_key="CONTRACEPT_YN",
            field_template_id=12,
        )

        self.assertEqual(snapshot, "1")
        self.assertEqual(storage_key, "CONTRACEPT_YN")
        self.assertEqual(
            DjangoReconcileDataQueryWriteRepository._jsonpath_for_field_key(storage_key),
            "$.CONTRACEPT_YN",
        )

    def test_close_query_sets_closed_by_id_to_actor_user(self):
        repository = DjangoReconcileDataQueryWriteRepository()
        query = _UpdateQuery()
        with patch(
            "apps.reconcile.infrastructure.repositories.dataquery_write.ReconcileDataQuery.objects.filter",
            return_value=query,
        ):
            closed = repository.close_query(
                dataquery_id=101,
                page_state_id=23,
                field_template_id=11,
                resolution_note="Done",
                actor_user_id=7,
                now="now",
                is_resolved=True,
            )

        self.assertIs(closed, True)
        self.assertEqual(query.updated_with["status"], "closed")
        self.assertEqual(query.updated_with["resolved_at"], "now")
        self.assertEqual(query.updated_with["resolved_by_id"].name, "answered_by_id")
        self.assertEqual(query.updated_with["closed_at"], "now")
        self.assertEqual(query.updated_with["closed_by_id"], 7)
        self.assertEqual(query.updated_with["updated_by_id"], 7)

    def test_close_query_returns_false_when_not_resolved(self):
        repository = DjangoReconcileDataQueryWriteRepository()

        closed = repository.close_query(
            dataquery_id=101,
            page_state_id=23,
            field_template_id=11,
            resolution_note="Done",
            actor_user_id=7,
            now="now",
            is_resolved=False,
        )

        self.assertIs(closed, False)

    def test_mark_query_answered_sets_answered_at_and_answered_by_id(self):
        repository = DjangoReconcileDataQueryWriteRepository()
        query = _UpdateQuery()
        with patch(
            "apps.reconcile.infrastructure.repositories.dataquery_write.ReconcileDataQuery.objects.filter",
            return_value=query,
        ):
            answered = repository.mark_query_answered(
                dataquery_id=101,
                page_state_id=23,
                field_template_id=11,
                actor_user_id=7,
                now="now",
            )

        self.assertIs(answered, True)
        self.assertEqual(query.updated_with["answered_at"], "now")
        self.assertEqual(query.updated_with["answered_by_id"], 7)
        self.assertEqual(query.updated_with["updated_at"], "now")
        self.assertEqual(query.updated_with["updated_by_id"], 7)

    def test_cancel_query_sets_cancelled_status(self):
        repository = DjangoReconcileDataQueryWriteRepository()
        query = _UpdateQuery()
        with patch(
            "apps.reconcile.infrastructure.repositories.dataquery_write.ReconcileDataQuery.objects.filter",
            return_value=query,
        ):
            cancelled = repository.cancel_query(
                dataquery_id=101,
                page_state_id=23,
                field_template_id=11,
                actor_user_id=7,
                now="now",
            )

        self.assertIs(cancelled, True)
        self.assertEqual(query.updated_with["status"], "cancelled")
        self.assertEqual(query.updated_with["updated_at"], "now")
        self.assertEqual(query.updated_with["updated_by_id"], 7)


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


class _ReplyRepositoryStub:
    def __init__(self, *, can_respond=True):
        self.created_threads = []
        self.answered_calls = []
        self.closed_calls = []
        self.cancelled_calls = []
        self.can_respond = can_respond

    def query_belongs_to_scope(self, **kwargs):
        self.scope_check = kwargs
        return True

    def user_can_respond_to_query(self, **kwargs):
        self.response_actor_check = kwargs
        return self.can_respond

    def create_query_thread_message(self, **kwargs):
        self.created_threads.append(kwargs)
        return SimpleNamespace(
            message_text=kwargs["message_text"],
            message_type=kwargs["message_type"],
            created_at=kwargs["now"],
        )

    def mark_query_answered(self, **kwargs):
        self.answered_calls.append(kwargs)
        return True

    def close_query(self, **kwargs):
        self.closed_calls.append(kwargs)
        return True

    def cancel_query(self, **kwargs):
        self.cancelled_calls.append(kwargs)
        return True


class _ReconcileRepositoryWithEntryContext(DjangoReconcileDataQueryWriteRepository):
    @classmethod
    def _current_page_entry_query_context(cls, *, page_state_id, field_template_id):
        return {
            "page_entry_id": 301,
            "value_snapshot": "1",
            "field_path": "$.CONTRACEPT_YN",
            "data_version": "v2",
            "assigned_to_id": 42,
        }


class _UpdateQuery:
    def __init__(self):
        self.updated_with = None

    def exclude(self, **kwargs):
        self.excluded_with = kwargs
        return self

    def update(self, **kwargs):
        self.updated_with = kwargs
        return 1
