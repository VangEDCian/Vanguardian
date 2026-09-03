from django.db import transaction
from django.utils import timezone

from apps.study.infrastructure.persistence.models import Study, StudyCrfPageLifecycleStep


class DjangoStudyCrfPageLifecycleRepository:
    def is_configured(self, *, study_id: int) -> bool:
        return bool(
            Study.objects.filter(pk=study_id).values_list(
                "crf_page_lifecycle_configured", flat=True
            ).first()
        )

    def list_steps(self, *, study_id: int):
        return list(
            StudyCrfPageLifecycleStep.objects.filter(study_id=study_id).order_by(
                "display_order", "id"
            )
        )

    @transaction.atomic
    def replace_steps(self, *, study_id: int, steps, actor_user_id: int | None):
        now = timezone.now()
        StudyCrfPageLifecycleStep.objects.filter(study_id=study_id).delete()
        created = StudyCrfPageLifecycleStep.objects.bulk_create(
            [
                StudyCrfPageLifecycleStep(
                    created_at=now,
                    updated_at=now,
                    study_id=study_id,
                    step_code=step.step_code,
                    display_order=index,
                    allowed_role_ids=list(step.allowed_role_ids),
                    created_by_id=actor_user_id,
                    updated_by_id=actor_user_id,
                )
                for index, step in enumerate(steps, start=1)
            ]
        )
        Study.objects.filter(pk=study_id).update(
            crf_page_lifecycle_configured=True,
            updated_at=now,
            updated_by_id=actor_user_id,
        )
        return created


__all__ = ["DjangoStudyCrfPageLifecycleRepository"]
