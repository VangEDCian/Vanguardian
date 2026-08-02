from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.study.models import Site, Study
from apps.subject.application.services.bulk_actions import SubjectBulkActionService
from apps.subject.application.services.event_instance_resync import (
    SubjectEventInstanceResyncResult,
    SubjectEventInstanceResyncService,
)
from apps.subject.infrastructure.repositories.bulk_actions import (
    DjangoSubjectBulkActionRepository,
    SubjectBulkActionSnapshot,
)
from apps.subject.models import Subject
from apps.subject.presentation.web.forms import SubjectBulkActionForm
from apps.subject.presentation.web.views.bulk_actions import SubjectBulkActionView


class SubjectBulkActionFormTests(SimpleTestCase):
    def test_normalizes_and_deduplicates_selected_subject_ids(self):
        form = SubjectBulkActionForm(
            {
                "action": "resync_stage",
                "subject_ids": ["20", "21", "20"],
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["subject_ids"], (20, 21))

    def test_requires_at_least_one_selected_subject(self):
        form = SubjectBulkActionForm({"action": "delete"})

        self.assertFalse(form.is_valid())
        self.assertIn("subject_ids", form.errors)


class SubjectBulkActionServiceTests(SimpleTestCase):
    def test_delete_soft_deletes_only_scoped_subjects_and_records_audit(self):
        repository = _BulkRepositoryStub(scoped_ids=(20, 21))
        audit_adapter = _AuditAdapterStub()
        service = SubjectBulkActionService(
            repository=repository,
            resync_service=Mock(),
            early_termination_service=Mock(),
            audit_context_adapter=audit_adapter,
        )

        result = SubjectBulkActionService.delete_subjects.__wrapped__(
            service,
            study_id=1,
            site_id=2,
            subject_ids=(20, 21, 30),
            actor_user_id=99,
            ip_address="127.0.0.1",
            user_agent="test",
        )

        self.assertEqual(repository.deleted_ids, (20, 21))
        self.assertEqual(result.succeeded_count, 2)
        self.assertEqual(result.out_of_scope_count, 1)
        self.assertEqual([call["object_id"] for call in audit_adapter.calls], ["20", "21"])
        self.assertTrue(all(call["after_data"]["deleted"] for call in audit_adapter.calls))

    def test_resync_runs_once_for_scoped_subjects(self):
        repository = _BulkRepositoryStub(scoped_ids=(20, 21))
        resync_service = _ResyncServiceStub()
        service = SubjectBulkActionService(
            repository=repository,
            resync_service=resync_service,
            early_termination_service=Mock(),
            audit_context_adapter=Mock(),
        )

        result = service.resync_subjects(
            study_id=1,
            site_id=2,
            subject_ids=(20, 21, 30),
            actor_user_id=99,
        )

        self.assertEqual(resync_service.calls[0]["subject_ids"], (20, 21))
        self.assertEqual(result.succeeded_count, 2)
        self.assertEqual(result.out_of_scope_count, 1)

    def test_early_termination_keeps_service_guards_for_each_subject(self):
        repository = _BulkRepositoryStub(scoped_ids=(20, 21))
        early_termination_service = _EarlyTerminationServiceStub()
        service = SubjectBulkActionService(
            repository=repository,
            resync_service=Mock(),
            early_termination_service=early_termination_service,
            audit_context_adapter=Mock(),
        )

        result = SubjectBulkActionService.start_early_termination.__wrapped__(
            service,
            study_id=1,
            site_id=2,
            subject_ids=(20, 21, 30),
            actor_user_id=99,
            effective_at="2026-08-02T10:00",
            reason_code="other",
            reason_text="Bulk termination",
        )

        self.assertEqual([call["subject_id"] for call in early_termination_service.calls], [20, 21])
        self.assertEqual(result.succeeded_count, 1)
        self.assertEqual(result.skipped_count, 1)
        self.assertEqual(result.out_of_scope_count, 1)
        self.assertEqual(result.reason_counts, (("subject_lifecycle_not_active", 1),))


class SubjectBulkActionRepositoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        now = timezone.now()
        cls.study = Study.objects.create(
            code="BULK-STUDY",
            name="Bulk Study",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        cls.other_study = Study.objects.create(
            code="BULK-OTHER",
            name="Other Bulk Study",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        cls.site = cls._create_site(cls.study, "BULK-SITE")
        cls.other_site = cls._create_site(cls.study, "BULK-SITE-OTHER")
        cls.other_study_site = cls._create_site(
            cls.other_study,
            "BULK-OTHER-STUDY-SITE",
        )
        cls.subject = cls._create_subject(cls.study, cls.site, 1)
        cls.other_site_subject = cls._create_subject(
            cls.study,
            cls.other_site,
            2,
        )
        cls.other_study_subject = cls._create_subject(
            cls.other_study,
            cls.other_study_site,
            1,
        )

    def setUp(self):
        self.repository = DjangoSubjectBulkActionRepository()

    def test_lists_only_active_subjects_in_the_authorized_study_site(self):
        subject_ids = self.repository.list_scoped_subject_ids(
            study_id=self.study.pk,
            site_id=self.site.pk,
            subject_ids=(
                self.subject.pk,
                self.other_site_subject.pk,
                self.other_study_subject.pk,
            ),
        )

        self.assertEqual(subject_ids, (self.subject.pk,))

    def test_soft_delete_preserves_record_and_updates_actor(self):
        deleted_count = self.repository.soft_delete_subjects(
            subject_ids=(self.subject.pk,),
            actor_user_id=99,
        )

        self.subject.refresh_from_db()
        self.assertEqual(deleted_count, 1)
        self.assertTrue(self.subject.deleted)
        self.assertEqual(self.subject.updated_by_id, 99)

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


class SubjectBulkActionViewTests(SimpleTestCase):
    def test_resolves_dedicated_permission_for_each_action(self):
        request_factory = RequestFactory()
        expected_permissions = {
            "delete": "subject.delete_subject",
            "resync_stage": "SUBJECT.UPDATE",
            "early_terminate": "SUBJECT.EARLY_TERMINATE",
        }

        for action, permission in expected_permissions.items():
            view = SubjectBulkActionView()
            view.request = request_factory.post("/bulk-action/", {"action": action})
            self.assertEqual(view.get_permission_required(), (permission,))

    def test_invalid_action_fails_closed_to_unassigned_permission(self):
        view = SubjectBulkActionView()
        view.request = RequestFactory().post("/bulk-action/", {"action": "unknown"})

        self.assertEqual(
            view.get_permission_required(),
            (SubjectBulkActionView.invalid_action_permission,),
        )

    def test_post_resyncs_selected_subjects_for_authorized_site(self):
        request = RequestFactory().post(
            "/bulk-action/",
            {
                "action": "resync_stage",
                "subject_ids": ["20", "21"],
                "next": "/studies/1/subjects/?page=2",
            },
        )
        request.user = SimpleNamespace(pk=99, is_authenticated=True)
        view = SubjectBulkActionView()
        view.service_class = _BulkViewServiceStub
        view.get_permission_authorization_context = lambda: SimpleNamespace(
            study_site_id=2
        )
        _BulkViewServiceStub.calls = []

        with patch(
            "apps.subject.presentation.web.views.bulk_actions.messages"
        ) as messages:
            response = view.post(request, study_id=1)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/studies/1/subjects/?page=2")
        self.assertEqual(
            _BulkViewServiceStub.calls[0]["subject_ids"],
            (20, 21),
        )
        self.assertEqual(_BulkViewServiceStub.calls[0]["site_id"], 2)
        messages.success.assert_called_once()


class SubjectBulkActionsTemplateTests(SimpleTestCase):
    def test_renders_bulk_action_row_and_forms_when_permitted(self):
        rendered = render_to_string(
            "subject/includes/subject_bulk_actions.html",
            {
                "can_delete_subject": True,
                "can_bulk_resync_subject": True,
                "can_bulk_early_terminate_subject": True,
                "csrf_token": "test-token",
                "shared_study_selected_id": 1,
                "request": SimpleNamespace(
                    get_full_path="/studies/1/subjects/?page=2"
                ),
            },
        )

        self.assertIn("subject-bulk-actions", rendered)
        self.assertIn("Delete Subjects", rendered)
        self.assertIn("Resync Stage", rendered)
        self.assertIn("Start Early Termination", rendered)
        self.assertIn(
            reverse("subject:subject_bulk_action", kwargs={"study_id": 1}),
            rendered,
        )
        self.assertIn('name="action" value="delete"', rendered)
        self.assertIn('name="action" value="resync_stage"', rendered)
        self.assertIn('name="action" value="early_terminate"', rendered)

    def test_bulk_action_row_is_immediately_after_toolbar(self):
        source = Path("src/templates/subject/subjects.html").read_text()

        toolbar_index = source.index("_entity_table_toolbar2.html")
        actions_index = source.index("subject_bulk_actions.html")
        table_index = source.index("{% render_table table %}")
        self.assertLess(toolbar_index, actions_index)
        self.assertLess(actions_index, table_index)


class SubjectBulkResyncServiceTests(SimpleTestCase):
    def test_resolves_active_version_once_for_multiple_subjects(self):
        repository = SimpleNamespace(
            resolve_active_study_version=Mock(return_value="v2.0")
        )
        service = SubjectEventInstanceResyncService(
            repository=repository,
            transition_service=Mock(),
            event_fact_provider=Mock(),
            event_data_status_provider=Mock(),
        )
        result = SubjectEventInstanceResyncResult(
            study_id=1,
            study_version="v2.0",
            subject_count=2,
        )
        service.resync_study_version = Mock(return_value=result)

        actual = service.resync_subjects_active_study_version(
            study_id=1,
            subject_ids=(20, 21),
            actor_user_id=99,
        )

        self.assertEqual(actual, result)
        repository.resolve_active_study_version.assert_called_once_with(study_id=1)
        self.assertEqual(
            service.resync_study_version.call_args.kwargs["subject_ids"],
            (20, 21),
        )


class _BulkRepositoryStub:
    def __init__(self, *, scoped_ids):
        self.scoped_ids = scoped_ids
        self.deleted_ids = ()

    def list_scoped_subject_ids(self, **_kwargs):
        return self.scoped_ids

    def list_scoped_subjects_for_update(self, **_kwargs):
        return tuple(
            SubjectBulkActionSnapshot(
                subject_id=subject_id,
                subject_code=f"SUBJ-{subject_id}",
                screening_code=f"SCR-{subject_id}",
                lifecycle_status="active",
            )
            for subject_id in self.scoped_ids
        )

    def soft_delete_subjects(self, *, subject_ids, actor_user_id):
        self.deleted_ids = subject_ids
        self.actor_user_id = actor_user_id
        return len(subject_ids)


class _AuditAdapterStub:
    def __init__(self):
        self.calls = []

    def record_event(self, **kwargs):
        self.calls.append(kwargs)


class _ResyncServiceStub:
    def __init__(self):
        self.calls = []

    def resync_subjects_active_study_version(self, **kwargs):
        self.calls.append(kwargs)
        return SubjectEventInstanceResyncResult(
            study_id=kwargs["study_id"],
            study_version="v2.0",
            subject_count=len(kwargs["subject_ids"]),
        )


class _EarlyTerminationServiceStub:
    def __init__(self):
        self.calls = []

    def request(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            requested=kwargs["subject_id"] == 20,
            reason=(
                "early_termination_started"
                if kwargs["subject_id"] == 20
                else "subject_lifecycle_not_active"
            ),
        )


class _BulkViewServiceStub:
    calls = []

    def resync_subjects(self, **kwargs):
        type(self).calls.append(kwargs)
        resync_result = SubjectEventInstanceResyncResult(
            study_id=kwargs["study_id"],
            study_version="v2.0",
            subject_count=len(kwargs["subject_ids"]),
        )
        return SimpleNamespace(
            selected_count=len(kwargs["subject_ids"]),
            scoped_count=len(kwargs["subject_ids"]),
            succeeded_count=len(kwargs["subject_ids"]),
            skipped_count=0,
            out_of_scope_count=0,
            reason_counts=(),
            resync_result=resync_result,
        )
