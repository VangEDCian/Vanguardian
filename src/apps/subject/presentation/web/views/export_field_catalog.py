from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views import View

from apps.shared.views import AuthenticateTemplateContextMixin
from apps.study.public import list_subject_export_field_groups
from apps.subject.presentation.web.views.base import SubjectAbstractVerifyStudy


class SubjectExportFieldCatalogView(
    AuthenticateTemplateContextMixin,
    SubjectAbstractVerifyStudy,
    View,
):
    permission_required = "DATA_EXPORT.RUN"
    authorization_scope = "STUDY_SITE"
    require_site_context = True
    raise_exception = True
    field_catalog_loader = staticmethod(list_subject_export_field_groups)

    def get(self, request, *args, **kwargs):
        html = render_to_string(
            "subject/includes/subject_export_field_groups.html",
            {
                "subject_export_field_groups": self.field_catalog_loader(
                    study_id=self.get_study_id(),
                ),
            },
        )
        return HttpResponse(html)


__all__ = ["SubjectExportFieldCatalogView"]
