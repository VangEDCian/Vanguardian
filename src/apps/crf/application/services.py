from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from apps.crf.models import CrfPageTemplate, CrfTemplate


class CrfTemplateNotFoundError(Exception):
    """Raised when a CRF template cannot be found for the requested selector."""


class CrfTemplateAmbiguousError(Exception):
    """Raised when a CRF template selector matches more than one template."""


class CrfTemplateApplicationService:
    template_model = CrfTemplate
    page_template_model = CrfPageTemplate

    def get_crf_template_model(self):
        return self.template_model

    def list_study_templates_for_listing(self, *, study_id):
        return self.template_model.objects.filter(
            study_id=study_id,
            deleted=False,
        ).prefetch_related("translations")

    def list_study_crf_navigation(self, *, study_id):
        page_template_qs = self.page_template_model.objects.filter(
            deleted=False,
        ).prefetch_related(
            "translations",
        ).order_by("order", "id")

        crf_templates = list(
            self.template_model.objects.filter(
                study_id=study_id,
                deleted=False,
            ).prefetch_related(
                "translations",
                Prefetch("page_templates", queryset=page_template_qs),
            ).order_by("code", "id")
        )

        return [
            {
                "id": str(crf_template.pk),
                "code": crf_template.code,
                "name": crf_template.safe_translation_getter(
                    "name",
                    default=crf_template.code,
                    any_language=True,
                ),
                "version": crf_template.version,
                "pages": [
                    {
                        "id": str(page_template.pk),
                        "code": page_template.code,
                        "title": page_template.safe_translation_getter(
                            "title",
                            default=page_template.code,
                            any_language=True,
                        ),
                        "order": page_template.order,
                    }
                    for page_template in crf_template.page_templates.all()
                ],
            }
            for crf_template in crf_templates
        ]

    def resolve_unique_template_by_code(
        self,
        *,
        study_id,
        code,
        case_insensitive=False,
    ):
        lookup_key = "code__iexact" if case_insensitive else "code"
        queryset = self.template_model.objects.filter(
            study_id=study_id,
            deleted=False,
            **{lookup_key: code},
        ).order_by("pk")

        count = queryset.count()
        if count == 0:
            raise CrfTemplateNotFoundError(
                f"CRF template with code '{code}' was not found for study '{study_id}'."
            )
        if count > 1:
            raise CrfTemplateAmbiguousError(
                f"CRF template code '{code}' is ambiguous for study '{study_id}'."
            )
        return queryset.first()

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
        timestamp = now or timezone.now()
        defaults = {
            "deleted": False,
            "is_active": True,
            "updated_at": timestamp,
            "updated_by_id": actor_user_id,
        }

        with transaction.atomic():
            crf_template = self.template_model.objects.filter(
                study_id=study_id,
                code=code,
                version=version,
            ).first()

            if crf_template is None:
                crf_template = self.template_model(
                    study_id=study_id,
                    code=code,
                    version=version,
                    created_at=timestamp,
                    created_by_id=actor_user_id,
                    **defaults,
                )
                import_outcome = "created"
            else:
                for field_name, value in defaults.items():
                    setattr(crf_template, field_name, value)
                import_outcome = "updated"

            self._set_translated_value(crf_template, "name", "vi", vi_name)
            self._set_translated_value(crf_template, "name", "en", en_name)
            crf_template.save()
            return import_outcome

    def upsert_crf_page_template(
        self,
        *,
        study_id,
        crf_code,
        code,
        title_vi,
        title_en,
        order,
        actor_user_id,
        now=None,
    ):
        crf_template = self.resolve_unique_template_by_code(
            study_id=study_id,
            code=crf_code,
            case_insensitive=False,
        )

        timestamp = now or timezone.now()
        defaults = {
            "deleted": False,
            "order": order,
            "updated_at": timestamp,
            "updated_by_id": actor_user_id,
        }

        with transaction.atomic():
            page_template = self.page_template_model.objects.filter(
                crf_template=crf_template,
                code=code,
            ).first()

            if page_template is None:
                page_template = self.page_template_model(
                    crf_template=crf_template,
                    code=code,
                    created_at=timestamp,
                    created_by_id=actor_user_id,
                    **defaults,
                )
                import_outcome = "created"
            else:
                for field_name, value in defaults.items():
                    setattr(page_template, field_name, value)
                import_outcome = "updated"

            self._set_translated_value(page_template, "title", "vi", title_vi)
            self._set_translated_value(page_template, "title", "en", title_en)
            page_template.save()
            return import_outcome

    @staticmethod
    def _set_translated_value(instance, field_name, language_code, value):
        instance.set_current_language(language_code, initialize=True)
        setattr(instance, field_name, value)
