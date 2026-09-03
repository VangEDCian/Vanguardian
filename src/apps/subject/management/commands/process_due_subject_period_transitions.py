from django.core.management.base import BaseCommand

from apps.subject.application.services.due_period_transition import (
    SubjectDuePeriodTransitionService,
)


class Command(BaseCommand):
    help = "Advance randomized subject periods whose washout end is due."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=500)
        parser.add_argument("--actor-user-id", type=int, default=None)

    def handle(self, *args, **options):
        result = SubjectDuePeriodTransitionService().process_due_transitions(
            actor_user_id=options["actor_user_id"],
            limit=max(1, options["limit"]),
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {result.due_subject_count} due subject(s); "
                f"advanced {result.advanced_subject_count}; "
                f"completed {result.workflow_event_count} washout event(s)."
            )
        )


__all__ = ["Command"]
