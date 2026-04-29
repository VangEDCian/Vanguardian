from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from django_filters.views import FilterView
from django_tables2 import SingleTableMixin

from apps.shared.context_processors import StudyDropdownHandler
from apps.shared.views import AuthenticateTemplateContextMixin
from apps.subject.models import Subject
from apps.subject.presentation.web.forms import SubjectsToolbarForm
from apps.subject.presentation.web.tables import SubjectListTable
from apps.subject.presentation.web.views.base import SubjectAbstractVerifyStudy


class SubjectListView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuthenticateTemplateContextMixin,
    SingleTableMixin,
    FilterView,
    ListView,
    SubjectAbstractVerifyStudy,
):
    permission_required = "subject.view_subject_list"
    raise_exception = True
    layout_nav_key = "SUBJECTS"
    layout_breadcrumb_label = _("SUBJECTS")

    model = Subject
    template_name = "subject/subjects.html"
    table_class = SubjectListTable
    filterset_class = SubjectsToolbarForm
    paginate_by = 25

    @staticmethod
    def _get_resolved_study_id(request):
        return StudyDropdownHandler(request=request).build().selected_id

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(study_id=self.get_study_id(), deleted=False)
            .select_related("site", "study", "enrollment", "randomization")
            .order_by("current_sequence", "id")
        )

    def get(self, request, *args, **kwargs):
        path_study_id = self.get_study_id()
        resolved_study_id = self._get_resolved_study_id(request)
        if path_study_id and resolved_study_id:
            if path_study_id == resolved_study_id:
                return super().get(request, *args, **kwargs)
            return redirect(
                reverse(
                    "subject:subject_list",
                    kwargs={"study_id": resolved_study_id},
                )
            )
        return redirect(reverse("dashboard:main"))
