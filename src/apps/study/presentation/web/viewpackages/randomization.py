from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404

from apps.shared.views.generic import AuthenticateTemplateView
from apps.study.application import (
    StudyDirectoryQueryService,
    StudyNotFoundError,
    StudyRandomizationDirectoryQueryService,
)
from apps.study.infrastructure.persistence.models import Study
from apps.study.presentation.web.viewpackages._helpers import _user_has_study_access

__all__ = ["StudyRandomizationView"]


class StudyRandomizationView(
    LoginRequiredMixin, PermissionRequiredMixin, AuthenticateTemplateView
):
    permission_required = "study.view_study_detail"
    raise_exception = True
    template_name = "study/randomization.html"
    layout_nav_key = "STUDIES"
    study_directory_query_service_class = StudyDirectoryQueryService
    study_randomization_directory_query_service_class = (
        StudyRandomizationDirectoryQueryService
    )
    _detail_view_model = None
    _study = None

    def get_study_directory_query_service(self):
        return self.study_directory_query_service_class()

    def get_study_randomization_directory_query_service(self):
        return self.study_randomization_directory_query_service_class()

    def dispatch(self, request, *args, **kwargs):
        self._study = Study.objects.filter(pk=kwargs["study_id"], deleted=False).first()
        if self._study is None:
            raise Http404

        try:
            self._detail_view_model = (
                self.get_study_directory_query_service().get_study_detail(
                    study_id=kwargs["study_id"]
                )
            )
        except StudyNotFoundError as exc:
            raise Http404 from exc

        if not _user_has_study_access(request.user, kwargs["study_id"]):
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)

    def get_layout_breadcrumb_label(self):
        if self._detail_view_model is None:
            return super().get_layout_breadcrumb_label()
        return self._detail_view_model["layout_breadcrumb_label"]

    def get_layout_show_breadcrumb_trail(self):
        return False

    def get_layout_detail_meta_items(self):
        if self._detail_view_model is None:
            return super().get_layout_detail_meta_items()
        return self._detail_view_model.get("layout_detail_meta_items", ())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["detail_study"] = self._detail_view_model["detail_study"]
        context.update(
            self.get_study_randomization_directory_query_service().get_overview(
                study_id=self._study.pk
            )
        )
        return context
