from apps.crf.application import (
    CrfTemplateAmbiguousError,
    CrfTemplateApplicationService,
    CrfTemplateNotFoundError,
)


class CrfContextAdapter:
    def __init__(self, crf_template_service=None):
        self.crf_template_service = crf_template_service or CrfTemplateApplicationService()

    def get_crf_template_model(self):
        return self.crf_template_service.get_crf_template_model()

    def list_study_templates_for_listing(self, *, study_id):
        return self.crf_template_service.list_study_templates_for_listing(study_id=study_id)

    def list_study_crf_navigation(self, *, study_id):
        return self.crf_template_service.list_study_crf_navigation(study_id=study_id)

    def list_template_fields_with_ui_config(self, *, template_id):
        return self.crf_template_service.list_template_fields_with_ui_config(
            template_id=template_id,
        )

    def resolve_unique_template_by_code(self, *, study_id, code, case_insensitive=False):
        return self.crf_template_service.resolve_unique_template_by_code(
            study_id=study_id,
            code=code,
            case_insensitive=case_insensitive,
        )

    def upsert_crf_template(
        self,
        *,
        study_id,
        code,
        version,
        vi_name,
        en_name,
        actor_user_id,
        now=None,
    ):
        return self.crf_template_service.upsert_crf_template(
            study_id=study_id,
            code=code,
            version=version,
            vi_name=vi_name,
            en_name=en_name,
            actor_user_id=actor_user_id,
            now=now,
        )


def get_crf_template_model():
    return CrfContextAdapter().get_crf_template_model()


__all__ = [
    "CrfContextAdapter",
    "CrfTemplateNotFoundError",
    "CrfTemplateAmbiguousError",
    "get_crf_template_model",
]
