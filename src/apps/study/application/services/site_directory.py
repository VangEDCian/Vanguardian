from django.core import serializers

from apps.study.infrastructure.repositories import DjangoStudyDirectoryRepository


class StudySiteDirectoryQueryService:
    repository_class = DjangoStudyDirectoryRepository

    @classmethod
    def get_active_studies(cls, user):
        return cls.repository_class().list_active_studies(user=user)

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

    @classmethod
    def get_study_id(cls, study_id):
        if study_id:
            return cls.repository_class().get_study(study_id=study_id)
        return None

    @classmethod
    def snapshot_site_obj(cls, site, refresh_from_db: bool = False) -> str:
        if refresh_from_db:
            site.refresh_from_db()
        return serializers.serialize("json", [site])

    @classmethod
    def study_site_belongs_to_study(cls, *, study_id: int, study_site_id: int) -> bool:
        return cls.repository_class().study_site_belongs_to_study(
            study_id=study_id,
            study_site_id=study_site_id,
        )
