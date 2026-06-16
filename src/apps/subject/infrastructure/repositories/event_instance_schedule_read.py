from apps.subject.models import SubjectEventInstance


class DjangoSubjectEventInstanceScheduleReadRepository:
    def get_event_start_datetime(self, *, event_instance_id: int):
        row = (
            SubjectEventInstance.objects.filter(pk=event_instance_id, deleted=False)
            .values("opened_at", "planned_date", "actual_date")
            .first()
        )
        if not row:
            return None
        return row["opened_at"] or row["planned_date"] or row["actual_date"]


__all__ = ["DjangoSubjectEventInstanceScheduleReadRepository"]
