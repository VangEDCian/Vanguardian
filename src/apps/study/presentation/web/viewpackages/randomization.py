from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View

from apps.shared.views.generic import AuthenticateTemplateView
from apps.study.application import (
    CommitRandomizationImportCommand,
    CommitStudyRandomizationArmsImportService,
    CommitStudyRandomizationSchemesImportService,
    PreviewRandomizationImportCommand,
    PreviewStudyRandomizationArmsImportService,
    PreviewStudyRandomizationSchemesImportService,
    RandomizationImportDependencyError,
    RandomizationImportFormatError,
    RandomizationImportValidationError,
    StudyDirectoryQueryService,
    StudyNotFoundError,
    StudyRandomizationDirectoryQueryService,
)
from apps.study.infrastructure.persistence.models import Study
from apps.study.presentation.web.forms import RandomizationImportFileForm
from apps.study.presentation.web.viewpackages._helpers import _user_has_study_access

__all__ = [
    "StudyRandomizationView",
    "StudyRandomizationSchemeImportPreviewView",
    "StudyRandomizationSchemeImportCommitView",
    "StudyRandomizationArmImportPreviewView",
    "StudyRandomizationArmImportCommitView",
]


class StudyRandomizationAccessMixin:
    study_directory_query_service_class = StudyDirectoryQueryService
    _detail_view_model = None
    _study = None

    def get_study_directory_query_service(self):
        return self.study_directory_query_service_class()

    def dispatch(self, request, *args, **kwargs):
        self._study = Study.objects.filter(pk=kwargs["study_id"], deleted=False).first()
        if self._study is None:
            raise Http404

        try:
            self._detail_view_model = self.get_study_directory_query_service().get_study_detail(
                study_id=kwargs["study_id"],
            )
        except StudyNotFoundError as exc:
            raise Http404 from exc

        if not _user_has_study_access(request.user, kwargs["study_id"]):
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)


class StudyRandomizationView(
    StudyRandomizationAccessMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuthenticateTemplateView,
):
    permission_required = "study.view_study_detail"
    raise_exception = True
    template_name = "study/randomization.html"
    layout_nav_key = "STUDIES"
    study_randomization_directory_query_service_class = (
        StudyRandomizationDirectoryQueryService
    )

    def get_study_randomization_directory_query_service(self):
        return self.study_randomization_directory_query_service_class()

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
                study_id=self._study.pk,
            ),
        )
        context["can_manage_randomization_import"] = self.request.user.has_perm(
            "study.update_study",
        )
        context["randomization_scheme_preview_url"] = reverse(
            "study:study_randomization_scheme_import_preview",
            kwargs={"study_id": self._study.pk},
        )
        context["randomization_scheme_commit_url"] = reverse(
            "study:study_randomization_scheme_import_commit",
            kwargs={"study_id": self._study.pk},
        )
        context["randomization_arm_preview_url"] = reverse(
            "study:study_randomization_arm_import_preview",
            kwargs={"study_id": self._study.pk},
        )
        context["randomization_arm_commit_url"] = reverse(
            "study:study_randomization_arm_import_commit",
            kwargs={"study_id": self._study.pk},
        )
        context["randomization_page_url"] = reverse(
            "study:study_randomization",
            kwargs={"study_id": self._study.pk},
        )
        return context


class StudyRandomizationImportBaseView(
    StudyRandomizationAccessMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin,
    View,
):
    permission_required = "study.update_study"
    raise_exception = True
    import_form_class = RandomizationImportFileForm
    preview_title = _("Import Preview")

    def get_import_form(self):
        return self.import_form_class(self.request.POST, self.request.FILES)

    def build_command(self, uploaded_file):
        return PreviewRandomizationImportCommand(
            actor_user_id=self.request.user.pk,
            study_id=self._study.pk,
            file_name=uploaded_file.name,
            file_content=uploaded_file.read(),
        )

    def serialize_preview_result(self, preview_result):
        preview_rows = [list(row.values) for row in preview_result.preview_rows[:100]]
        issues = [
            {
                "row_number": issue.row_number,
                "identifier": issue.identifier,
                "column_label": issue.column_label,
                "reason": str(issue.reason),
                "detail": str(
                    _("Row %(row)s · %(column)s · %(reason)s")
                    % {
                        "row": issue.row_number,
                        "column": issue.column_label,
                        "reason": str(issue.reason),
                    },
                ),
            }
            for issue in preview_result.issues
        ]
        return {
            "title": str(self.preview_title),
            "headers": [column.label for column in preview_result.columns],
            "rows": preview_rows,
            "total_rows": preview_result.total_rows,
            "issue_count": len(preview_result.issues),
            "issues": issues,
            "can_commit": len(preview_result.issues) == 0,
        }

    def render_form_errors(self, form):
        return JsonResponse(
            {"errors": form.errors.get_json_data()},
            status=400,
        )

    def render_format_error(self, exc):
        return JsonResponse({"detail": str(exc)}, status=400)


class StudyRandomizationSchemeImportPreviewView(StudyRandomizationImportBaseView):
    preview_service_class = PreviewStudyRandomizationSchemesImportService
    preview_title = _("Randomization Scheme Preview")

    def get_preview_service(self):
        return self.preview_service_class()

    def post(self, request, *_args, **_kwargs):
        form = self.get_import_form()
        if not form.is_valid():
            return self.render_form_errors(form)

        uploaded_file = form.cleaned_data["import_file"]
        try:
            preview_result = self.get_preview_service().execute(self.build_command(uploaded_file))
        except (RandomizationImportDependencyError, RandomizationImportFormatError) as exc:
            return self.render_format_error(exc)

        return JsonResponse(self.serialize_preview_result(preview_result))


class StudyRandomizationArmImportPreviewView(StudyRandomizationImportBaseView):
    preview_service_class = PreviewStudyRandomizationArmsImportService
    preview_title = _("Randomization Arm Preview")

    def get_preview_service(self):
        return self.preview_service_class()

    def post(self, request, *_args, **_kwargs):
        form = self.get_import_form()
        if not form.is_valid():
            return self.render_form_errors(form)

        uploaded_file = form.cleaned_data["import_file"]
        try:
            preview_result = self.get_preview_service().execute(self.build_command(uploaded_file))
        except (RandomizationImportDependencyError, RandomizationImportFormatError) as exc:
            return self.render_format_error(exc)

        return JsonResponse(self.serialize_preview_result(preview_result))


class StudyRandomizationCommitBaseView(StudyRandomizationImportBaseView):
    commit_service_class = None
    success_message = _("Import completed successfully.")

    def get_commit_service(self):
        return self.commit_service_class()

    def build_commit_command(self, uploaded_file):
        return CommitRandomizationImportCommand(
            actor_user_id=self.request.user.pk,
            study_id=self._study.pk,
            file_name=uploaded_file.name,
            file_content=uploaded_file.read(),
        )

    def serialize_validation_error(self, exc):
        return JsonResponse(
            {
                "detail": str(exc),
                "issues": [
                    {
                        "row_number": issue.row_number,
                        "identifier": issue.identifier,
                        "column_label": issue.column_label,
                        "reason": str(issue.reason),
                        "detail": str(
                            _("Row %(row)s · %(column)s · %(reason)s")
                            % {
                                "row": issue.row_number,
                                "column": issue.column_label,
                                "reason": str(issue.reason),
                            },
                        ),
                    }
                    for issue in exc.issues
                ],
            },
            status=400,
        )

    def build_success_payload(self, import_result):
        return {
            "detail": str(
                self.success_message
                % {
                    "created_count": import_result.created_count,
                    "updated_count": import_result.updated_count,
                },
            ),
            "redirect_url": reverse(
                "study:study_randomization",
                kwargs={"study_id": self._study.pk},
            ),
        }

    def post(self, request, *_args, **_kwargs):
        form = self.get_import_form()
        if not form.is_valid():
            return self.render_form_errors(form)

        uploaded_file = form.cleaned_data["import_file"]
        try:
            import_result = self.get_commit_service().execute(
                self.build_commit_command(uploaded_file),
            )
        except (RandomizationImportDependencyError, RandomizationImportFormatError) as exc:
            return self.render_format_error(exc)
        except RandomizationImportValidationError as exc:
            return self.serialize_validation_error(exc)

        return JsonResponse(self.build_success_payload(import_result))


class StudyRandomizationSchemeImportCommitView(StudyRandomizationCommitBaseView):
    commit_service_class = CommitStudyRandomizationSchemesImportService
    success_message = _(
        "Imported randomization schemes successfully. Created: %(created_count)s. Updated: %(updated_count)s.",
    )


class StudyRandomizationArmImportCommitView(StudyRandomizationCommitBaseView):
    commit_service_class = CommitStudyRandomizationArmsImportService
    success_message = _(
        "Imported randomization arms successfully. Created: %(created_count)s. Updated: %(updated_count)s.",
    )
