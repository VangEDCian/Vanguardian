from contextlib import nullcontext
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse
from django.utils import translation

from apps.core.choices import EventInstanceStatusChoices
from apps.subject.application.services.add_repeating_event_instance import (
    AddRepeatingSubjectEventInstanceService,
    CurrentRepeatingEventOpenError,
    MaxRepeatingEventInstancesExceededError,
)
from apps.subject.infrastructure.repositories.repeating_event_instance import (
    CreatedRepeatingEventInstanceSnapshot,
    DjangoSubjectRepeatingEventInstanceRepository,
    RepeatingEventDefinitionSnapshot,
    SubjectEventInstanceSummary,
    SubjectSnapshot,
)
from apps.subject.presentation.web.views.detail_navigation import SubjectDetailNavigationMixin
from apps.subject.presentation.web.views.repeating_event_instance import (
    SubjectAddRepeatingEventInstanceView,
)


class AddRepeatingSubjectEventInstanceServiceTests(SimpleTestCase):
    def test_creates_next_repeat_with_open_status(self):
        now = datetime(2026, 5, 18, 9, 30, tzinfo=timezone.utc)
        repository = _RepeatingEventRepositoryStub(
            now=now,
            event_instances=[
                SubjectEventInstanceSummary(id=1, status=EventInstanceStatusChoices.COMPLETED, repeat_index=1),
                SubjectEventInstanceSummary(id=2, status=EventInstanceStatusChoices.VERIFIED, repeat_index=2),
            ],
            max_repeats=3,
        )

        with patch(
            "apps.subject.application.services.add_repeating_event_instance.transaction.atomic",
            return_value=nullcontext(),
        ):
            created_event = AddRepeatingSubjectEventInstanceService(
                repository=repository
            ).execute(
                study_id=1,
                subject_id=20,
                event_definition_id=100,
                actor_user_id=99,
            )

        self.assertEqual(created_event.repeat_index, 3)
        self.assertEqual(created_event.status, EventInstanceStatusChoices.OPEN)
        self.assertEqual(repository.created_kwargs["repeat_index"], 3)
        self.assertEqual(repository.created_kwargs["now"], now)
        self.assertEqual(repository.created_kwargs["actor_user_id"], 99)

    def test_blocks_when_open_instance_exists(self):
        repository = _RepeatingEventRepositoryStub(
            event_instances=[
                SubjectEventInstanceSummary(id=1, status=EventInstanceStatusChoices.OPEN, repeat_index=1),
            ],
        )

        with (
            patch(
                "apps.subject.application.services.add_repeating_event_instance.transaction.atomic",
                return_value=nullcontext(),
            ),
            self.assertRaises(CurrentRepeatingEventOpenError),
        ):
            AddRepeatingSubjectEventInstanceService(repository=repository).execute(
                study_id=1,
                subject_id=20,
                event_definition_id=100,
                actor_user_id=99,
            )

        self.assertIsNone(repository.created_kwargs)

    def test_blocks_when_count_reaches_max_repeats(self):
        repository = _RepeatingEventRepositoryStub(
            event_instances=[
                SubjectEventInstanceSummary(id=1, status=EventInstanceStatusChoices.VERIFIED, repeat_index=1),
                SubjectEventInstanceSummary(id=2, status=EventInstanceStatusChoices.COMPLETED, repeat_index=2),
            ],
            max_repeats=2,
        )

        with (
            patch(
                "apps.subject.application.services.add_repeating_event_instance.transaction.atomic",
                return_value=nullcontext(),
            ),
            self.assertRaises(MaxRepeatingEventInstancesExceededError),
        ):
            AddRepeatingSubjectEventInstanceService(repository=repository).execute(
                study_id=1,
                subject_id=20,
                event_definition_id=100,
                actor_user_id=99,
            )

        self.assertIsNone(repository.created_kwargs)

    def test_allows_null_max_repeats(self):
        repository = _RepeatingEventRepositoryStub(
            event_instances=[
                SubjectEventInstanceSummary(id=1, status=EventInstanceStatusChoices.VERIFIED, repeat_index=1),
                SubjectEventInstanceSummary(id=2, status=EventInstanceStatusChoices.COMPLETED, repeat_index=2),
            ],
            max_repeats=None,
        )

        with patch(
            "apps.subject.application.services.add_repeating_event_instance.transaction.atomic",
            return_value=nullcontext(),
        ):
            created_event = AddRepeatingSubjectEventInstanceService(
                repository=repository
            ).execute(
                study_id=1,
                subject_id=20,
                event_definition_id=100,
                actor_user_id=99,
            )

        self.assertEqual(created_event.repeat_index, 3)


class SubjectAddRepeatingEventInstanceViewTests(SimpleTestCase):
    def test_post_success_redirects_to_new_event_and_adds_message(self):
        request = RequestFactory().post("/add-another/")
        request.user = SimpleNamespace(pk=99)
        view = SubjectAddRepeatingEventInstanceView()
        view.service_class = _SuccessfulAddRepeatingService

        with patch("apps.subject.presentation.web.views.repeating_event_instance.messages") as messages:
            response = view.post(
                request,
                study_id=1,
                subject_id=20,
                event_definition_id=100,
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            f"{reverse('subject:subject_detail', kwargs={'study_id': 1, 'subject_id': 20})}?event=55",
        )
        messages.success.assert_called_once()

    def test_post_blocked_redirects_back_and_adds_error_message(self):
        next_url = reverse("subject:subject_detail", kwargs={"study_id": 1, "subject_id": 20})
        request = RequestFactory().post("/add-another/", data={"next": next_url})
        request.user = SimpleNamespace(pk=99)
        view = SubjectAddRepeatingEventInstanceView()
        view.service_class = _BlockedAddRepeatingService

        with patch("apps.subject.presentation.web.views.repeating_event_instance.messages") as messages:
            response = view.post(
                request,
                study_id=1,
                subject_id=20,
                event_definition_id=100,
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], next_url)
        messages.error.assert_called_once()


class SubjectRepeatingEventInstanceRepositoryTests(SimpleTestCase):
    def test_create_open_repeating_event_instance_writes_initial_transition_log(self):
        now = datetime(2026, 5, 18, 9, 30, tzinfo=timezone.utc)
        subject = SubjectSnapshot(id=20, study_id=1)
        event_definition = RepeatingEventDefinitionSnapshot(
            id=100,
            study_id=1,
            study_version="1.0",
            code="UNSCHEDULED",
            name="Unscheduled Visit",
            event_type="visit_based",
            max_repeats=None,
        )
        created_model = SimpleNamespace(pk=55, status=EventInstanceStatusChoices.OPEN)

        with (
            patch(
                "apps.subject.infrastructure.repositories.repeating_event_instance."
                "SubjectEventInstance.objects.create",
                return_value=created_model,
            ) as create_event_instance,
            patch(
                "apps.subject.infrastructure.repositories.repeating_event_instance."
                "SubjectEventInstanceTransitionLog.objects.create",
            ) as create_transition_log,
        ):
            created_event = DjangoSubjectRepeatingEventInstanceRepository().create_open_repeating_event_instance(
                subject=subject,
                event_definition=event_definition,
                repeat_index=3,
                actor_user_id=99,
                now=now,
            )

        create_event_instance.assert_called_once()
        create_transition_log.assert_called_once_with(
            study_id=1,
            subject_id=20,
            source_event_instance_id=55,
            target_event_instance_id=None,
            transition_rule_id=None,
            from_event_definition_id=100,
            to_event_definition_id=None,
            from_status="not_created",
            to_status=EventInstanceStatusChoices.OPEN,
            trigger_source="add_repeating_event_instance",
            result="applied",
            reason="repeating_event_instance_created",
            facts_json="{}",
            created_at=now,
            updated_at=now,
            created_by_id=99,
            updated_by_id=99,
        )
        self.assertEqual(created_event.id, 55)
        self.assertEqual(created_event.repeat_index, 3)


class SubjectDetailNavigationRepeatingActionTests(SimpleTestCase):
    def test_repeating_navigation_uses_open_instance_as_parent_and_completed_instances_as_children(self):
        event_items = {
            100: [
                {
                    "id": "10",
                    "event_definition_id": "100",
                    "status": EventInstanceStatusChoices.COMPLETED,
                    "is_repeating": True,
                },
                {
                    "id": "11",
                    "event_definition_id": "100",
                    "status": EventInstanceStatusChoices.OPEN,
                    "is_repeating": True,
                },
                {
                    "id": "12",
                    "event_definition_id": "100",
                    "status": EventInstanceStatusChoices.VERIFIED,
                    "is_repeating": True,
                },
            ]
        }

        navigation = SubjectDetailNavigationMixin._collapse_repeating_event_navigation(event_items)

        self.assertEqual(navigation[0]["id"], "11")
        self.assertEqual([item["id"] for item in navigation[0]["repeat_event_instances"]], ["10"])

    def test_completed_at_label_uses_active_locale_date_format(self):
        completed_at = datetime(2026, 5, 18, 9, 30, tzinfo=timezone.utc)

        with translation.override("vi"):
            vi_label = SubjectDetailNavigationMixin._format_completed_at_label(completed_at)
        with translation.override("en"):
            en_label = SubjectDetailNavigationMixin._format_completed_at_label(completed_at)

        self.assertEqual(vi_label, "18/05/2026")
        self.assertEqual(en_label, "05/18/2026")

    def test_repeating_child_focus_urls_use_child_event_instance_id(self):
        repeat_event_instances = [
            {
                "id": "10",
                "forms": [
                    {
                        "id": "1",
                        "title": "Vitals",
                    }
                ],
            }
        ]

        navigation = SubjectDetailNavigationMixin._with_repeat_event_focus_urls(
            repeat_event_instances=repeat_event_instances,
            detail_url="/studies/1/subjects/20/",
            add_another_url="/add-another/",
        )

        self.assertEqual(navigation[0]["focus_url"], "/studies/1/subjects/20/?event=10")
        self.assertEqual(
            navigation[0]["forms"][0]["focus_url"],
            "/studies/1/subjects/20/?event=10&form=1",
        )

    def test_can_add_another_only_for_last_repeating_event_without_open_or_limit(self):
        self.assertFalse(
            SubjectDetailNavigationMixin._can_add_another_repeating_event(
                is_repeating=True,
                is_last_repeat_instance=False,
                has_open_event_instance=False,
                event_count=1,
                max_repeats=None,
            )
        )
        self.assertFalse(
            SubjectDetailNavigationMixin._can_add_another_repeating_event(
                is_repeating=True,
                is_last_repeat_instance=True,
                has_open_event_instance=True,
                event_count=1,
                max_repeats=None,
            )
        )
        self.assertFalse(
            SubjectDetailNavigationMixin._can_add_another_repeating_event(
                is_repeating=True,
                is_last_repeat_instance=True,
                has_open_event_instance=False,
                event_count=2,
                max_repeats=2,
            )
        )
        self.assertTrue(
            SubjectDetailNavigationMixin._can_add_another_repeating_event(
                is_repeating=True,
                is_last_repeat_instance=True,
                has_open_event_instance=False,
                event_count=2,
                max_repeats=None,
            )
        )


class SubjectDetailRepeatingEventFooterTests(SimpleTestCase):
    def test_repeating_add_another_button_renders_disabled_without_url(self):
        request = RequestFactory().get("/subjects/20/?event=55")
        request.user = SimpleNamespace(is_authenticated=False)

        html = render_to_string(
            "subject/includes/subject_detail_page_entry_footer.html",
            {
                "request": request,
                "focused_event": {
                    "is_repeating": True,
                    "add_another_url": "",
                    "add_another_label": "Add Another Unscheduled Visit",
                },
                "is_page_edit_locked": False,
                "datacapture_save_url": "/save/",
                "is_viewing_submitted_version": False,
                "view_current_url": "",
                "is_focused_render_draft_version": False,
                "focused_form": None,
                "event_file_import_url": "",
            },
            request=request,
        )

        self.assertIn("Add Another Unscheduled Visit", html)
        self.assertIn("disabled", html)


class _RepeatingEventRepositoryStub:
    def __init__(self, *, now=None, event_instances=(), max_repeats=None):
        self._now = now or datetime(2026, 5, 18, 9, 30, tzinfo=timezone.utc)
        self.event_instances = list(event_instances)
        self.max_repeats = max_repeats
        self.created_kwargs = None

    def now(self):
        return self._now

    def get_subject_for_update(self, **kwargs):
        return SubjectSnapshot(id=kwargs["subject_id"], study_id=kwargs["study_id"])

    def get_repeating_event_definition_for_update(self, **kwargs):
        return RepeatingEventDefinitionSnapshot(
            id=kwargs["event_definition_id"],
            study_id=kwargs["study_id"],
            study_version="1.0",
            code="UNSCHEDULED",
            name="Unscheduled Visit",
            event_type="visit_based",
            max_repeats=self.max_repeats,
        )

    def list_event_instances_for_update(self, **kwargs):
        return self.event_instances

    def get_next_repeat_index(self, **kwargs):
        return max((event.repeat_index for event in self.event_instances), default=0) + 1

    def create_open_repeating_event_instance(self, **kwargs):
        self.created_kwargs = kwargs
        return CreatedRepeatingEventInstanceSnapshot(
            id=55,
            event_definition_id=kwargs["event_definition"].id,
            event_name=kwargs["event_definition"].name,
            repeat_index=kwargs["repeat_index"],
            status=EventInstanceStatusChoices.OPEN,
        )


class _SuccessfulAddRepeatingService:
    def execute(self, **kwargs):
        return CreatedRepeatingEventInstanceSnapshot(
            id=55,
            event_definition_id=kwargs["event_definition_id"],
            event_name="Unscheduled Visit",
            repeat_index=2,
            status=EventInstanceStatusChoices.OPEN,
        )


class _BlockedAddRepeatingService:
    def execute(self, **kwargs):
        raise CurrentRepeatingEventOpenError()
