from apps.subject.models import SubjectMilestone


class DjangoSubjectMilestoneRepository:
    def get_current_milestone(self, *, milestone_id: int):
        return SubjectMilestone.objects.get(pk=milestone_id, deleted=False)

    def save_correction(
        self,
        *,
        milestone,
        occurred_at,
        occurred_date,
        occurred_time,
        date_precision,
        status,
        reason,
        actor_id,
        now,
    ):
        milestone.occurred_at = occurred_at
        milestone.occurred_date = occurred_date
        milestone.occurred_time = occurred_time
        milestone.date_precision = date_precision
        milestone.status = status
        milestone.correction_reason = reason
        milestone.updated_at = now
        milestone.updated_by_id = actor_id
        update_fields = [
            "occurred_at",
            "occurred_date",
            "occurred_time",
            "date_precision",
            "status",
            "correction_reason",
            "updated_at",
            "updated_by_id",
        ]
        milestone.save(update_fields=update_fields)
        return milestone


__all__ = ["DjangoSubjectMilestoneRepository"]
