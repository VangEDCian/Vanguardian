from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import Http404

from apps.crf.application.form_builder_queries import FormBuilderReadModelService
from apps.crf.domain.exceptions import FormScopeViolationError
from apps.shared.context_processors import StudyDropdownHandler
from apps.shared.views import AuthenticateTemplateView

class CrfFormDetailView(LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView):
    permission_required = "study.view_study_detail"
    raise_exception = True
    template_name = "crf/form_detail.html"
    layout_nav_key = "STUDIES"
    layout_show_breadcrumb_trail = False
    read_model_service_class = FormBuilderReadModelService

    def get_read_model_service(self):
        return self.read_model_service_class()

    def get_selected_study_id(self):
        return StudyDropdownHandler(request=self.request).build().selected_id

    def get_builder(self):
        if not hasattr(self, "_builder"):
            try:
                self._builder = self.get_read_model_service().get_builder(
                    form_id=self.kwargs["form_id"],
                )
            except FormScopeViolationError as exc:
                raise Http404 from exc
        return self._builder

    def ensure_study_scope(self, builder):
        selected_study_id = self.get_selected_study_id()
        if selected_study_id is None:
            raise Http404
        if int(builder["template"]["study_id"]) != int(selected_study_id):
            raise Http404
        return selected_study_id

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        builder = self.get_builder()
        selected_study_id = self.ensure_study_scope(builder)

        context.update(builder)
        context["detail_study"] = {"id": int(selected_study_id)}
        context["layout_breadcrumb_label"] = builder["template"]["code"]
        context["page_title"] = builder["template"]["name"] or builder["template"]["code"]
        context["fields_total"] = len(builder.get("fields", []))
        context["sections_total"] = len([section for section in builder.get("sections", []) if section.get("id") is not None])
        return context
