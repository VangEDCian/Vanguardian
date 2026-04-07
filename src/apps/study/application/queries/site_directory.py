from apps.identity.infrastructure.persistence.models import StudyMembership
from apps.study.infrastructure.persistence.models import Study


class StudySiteDirectoryQueryService:
    @classmethod
    def get_active_studies(cls, user):
        studies = Study.objects.filter(deleted=False)
        if not user.is_superuser:
            study_ids = StudyMembership.objects.filter(user=user, deleted=False).values_list(
                "study_id", flat=True,
            )
            studies = studies.filter(pk__in=study_ids)
        return studies.order_by("code")

    @classmethod
    def study_choices(cls, studies):
        return [(s.pk, f"{s.name}") for s in studies]

    @classmethod
    def build_site_study_options(cls, studies, selected_id=None):
        selected_str = str(selected_id) if selected_id is not None else None
        return [
            {
                "value": str(s.pk),
                "label": f"{s.code} – {s.name}",
                "selected": str(s.pk) == selected_str,
            }
            for s in studies
        ]
