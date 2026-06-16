from django.db.models import Q

from apps.crf.models import (
    CrfFieldTemplate,
    CrfFieldValidationRule,
    CrfTemplate,
)


class DjangoCrfValidationRuleImportRepository:
    def find_template_by_code_or_id(self, *, study_id, form_code):
        normalized_form_code = str(form_code or "").strip()
        queryset = CrfTemplate.objects.filter(
            study_id=study_id,
            deleted=False,
        )
        if normalized_form_code.isdigit():
            queryset = queryset.filter(Q(pk=int(normalized_form_code)) | Q(code__iexact=normalized_form_code))
        else:
            queryset = queryset.filter(code__iexact=normalized_form_code)
        return queryset.order_by("pk")

    def find_template_by_code(self, *, study_id, form_code):
        return CrfTemplate.objects.filter(
            study_id=study_id,
            code__iexact=str(form_code or "").strip(),
            deleted=False,
        ).order_by("pk")

    def find_field_by_name_or_id(self, *, crf_template_id, field_name):
        normalized_field_name = str(field_name or "").strip()
        queryset = CrfFieldTemplate.objects.filter(
            crf_template_id=crf_template_id,
            deleted=False,
        )
        if normalized_field_name.isdigit():
            queryset = queryset.filter(Q(pk=int(normalized_field_name)) | Q(field_key__iexact=normalized_field_name))
        else:
            queryset = queryset.filter(field_key__iexact=normalized_field_name)
        return queryset.order_by("pk")

    def find_field_by_key(self, *, crf_template_id, field_name):
        return CrfFieldTemplate.objects.filter(
            crf_template_id=crf_template_id,
            field_key__iexact=str(field_name or "").strip(),
            deleted=False,
        ).order_by("pk")

    def find_validation_rule_for_import(self, *, field_template_id, rule_type, expression, mode):
        return (
            CrfFieldValidationRule.objects.filter(
                field_template_id=field_template_id,
                rule_type=rule_type,
                expression=expression,
                mode=mode,
            )
            .order_by("pk")
            .first()
        )

    def build_validation_rule(self, **values):
        return CrfFieldValidationRule(**values)

    def save_validation_rule(self, validation_rule):
        validation_rule.save()
        return validation_rule
