import json
import logging

from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View

from apps.shared.views.generic import AuthenticateTemplateContextMixin, AuthenticateTemplateView
from apps.shared.navigation import user_can_access_permission
from apps.study.application import (
    CommitStudyRandomizationArmsImportService,
    CommitStudyRandomizationSchemesImportService,
    CommitStudyRandomizationSequencePeriodsImportService,
    PreviewStudyRandomizationArmsImportService,
    PreviewStudyRandomizationSchemesImportService,
    PreviewStudyRandomizationSequencePeriodsImportService,
    RandomizationImportDependencyError,
    RandomizationImportFormatError,
    RandomizationImportValidationError,
    StudyDirectoryQueryService,
    StudyNotFoundError,
    StudyRandomizationDirectoryQueryService,
)
from apps.study.application.services import BaseRandomizationImportValidationService
from apps.study.infrastructure.persistence.models import Study
from apps.study.presentation.web.forms import RandomizationImportFileForm
from apps.study.presentation.web.mappers.commands import (
    to_commit_randomization_import_command,
    to_preview_randomization_import_command,
)
from apps.study.presentation.web.views.helpers import _user_has_study_access

__all__ = [
    "StudyRandomizationView",
    "StudyRandomizationSchemeImportPreviewView",
    "StudyRandomizationSchemeImportCommitView",
    "StudyRandomizationArmImportPreviewView",
    "StudyRandomizationArmImportCommitView",
    "StudyRandomizationSequencePeriodImportPreviewView",
    "StudyRandomizationSequencePeriodImportCommitView",
]

logger = logging.getLogger(__name__)


class StudyRandomizationAccessMixin(View):
    study_directory_query_service_class = StudyDirectoryQueryService
    _detail_view_model = None
    _study = None

    def get_study_directory_query_service(self):
        return self.study_directory_query_service_class()

    def dispatch(self, request, *args, **kwargs):
        unauthenticated_response = self.dispatch_authenticated(request)
        if unauthenticated_response is not None:
            return unauthenticated_response
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
    AuthenticateTemplateView,
):
    permission_required = "study.view_study_detail"
    authorization_scope = "STUDY"
    raise_exception = True
    template_name = "study/randomization.html"
    layout_nav_key = "STUDIES"
    study_randomization_directory_query_service_class = StudyRandomizationDirectoryQueryService

    @staticmethod
    def _build_delete_cell(*, action_url, confirm_message, enabled):
        if not enabled:
            return {"kind": "muted", "value": "—"}
        return {
            "kind": "post_action",
            "action": action_url,
            "label": str(_("Delete")),
            "button_class": "randomization-delete-button",
            "confirm_message": str(confirm_message),
        }

    def _append_delete_actions(self, *, context):
        action_header = {"label": _("ACTIONS")}
        can_delete = context["can_manage_randomization_import"]

        scheme_headers = list(context.get("randomization_scheme_headers", ()))
        scheme_headers.append(action_header)
        context["randomization_scheme_headers"] = tuple(scheme_headers)
        for row in context.get("randomization_scheme_rows", []):
            row["cells"].append(
                self._build_delete_cell(
                    action_url=reverse(
                        "study:study_randomization_scheme_delete",
                        kwargs={"study_id": self._study.pk, "scheme_id": row["selection_value"]},
                    ),
                    confirm_message=_("Are you sure you want to delete this randomization scheme?"),
                    enabled=can_delete,
                ),
            )

        arm_headers = list(context.get("randomization_arm_headers", ()))
        arm_headers.append(action_header)
        context["randomization_arm_headers"] = tuple(arm_headers)
        for row in context.get("randomization_arm_rows", []):
            row["cells"].append(
                self._build_delete_cell(
                    action_url=reverse(
                        "study:study_randomization_arm_delete",
                        kwargs={"study_id": self._study.pk, "arm_id": row["selection_value"]},
                    ),
                    confirm_message=_("Are you sure you want to delete this randomization arm?"),
                    enabled=can_delete,
                ),
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
        context["can_manage_randomization_import"] = user_can_access_permission(
            self.request.user,
            "study.update_study",
            study_id=self._study.pk,
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
        context["randomization_sequence_period_preview_url"] = reverse(
            "study:study_randomization_sequence_period_import_preview",
            kwargs={"study_id": self._study.pk},
        )
        context["randomization_sequence_period_commit_url"] = reverse(
            "study:study_randomization_sequence_period_import_commit",
            kwargs={"study_id": self._study.pk},
        )
        context["randomization_page_url"] = reverse(
            "study:study_randomization",
            kwargs={"study_id": self._study.pk},
        )
        self._append_delete_actions(context=context)
        return context


class StudyRandomizationImportBaseView(
    StudyRandomizationAccessMixin,
    AuthenticateTemplateContextMixin,
    View,
):
    permission_required = "study.update_study"
    authorization_scope = "STUDY"
    raise_exception = True
    import_form_class = RandomizationImportFileForm
    preview_title = _("Import Preview")
    preview_service_class: BaseRandomizationImportValidationService | None = None
    field_input_guidance = {}
    preview_json_dump_type: tuple[type] = None

    def get_import_form(self):
        return self.import_form_class(self.request.POST, self.request.FILES)

    @classmethod
    def render_form_errors(cls, form):
        return JsonResponse(
            {
                "detail": str(_("Please upload a valid file.")),
                "errors": form.errors.get_json_data(),
            },
            status=400,
        )

    @classmethod
    def render_format_error(cls, exc):
        if isinstance(exc, RandomizationImportDependencyError):
            detail = str(
                _("Import processing is temporarily unavailable. Please contact support."),
            )
        elif isinstance(exc, RandomizationImportFormatError):
            detail = str(
                _("The uploaded file format is invalid. Please review the template and try again."),
            )
        else:
            detail = str(_("Unable to process import file."))

        logger.warning(
            "Randomization import request failed with %s",
            exc.__class__.__name__,
            exc_info=(exc.__class__, exc, exc.__traceback__),
        )
        return JsonResponse({"detail": detail}, status=400)

    def get_preview_service(self) -> BaseRandomizationImportValidationService:
        if (
                self.preview_service_class
                and callable(self.preview_service_class)
        ):
            return self.preview_service_class()
        raise ValueError(
            self.__class__.__name__,
            'property `preview_service_class` must be provide class '
            'extend from BaseRandomizationImportValidationService',
        )

    def build_command(self, uploaded_file):
        if self.request.user.pk and isinstance(self.request.user.pk, int):
            return to_preview_randomization_import_command(
                actor_user_id=self.request.user.pk,
                study_id=self._study.pk,
                file_name=uploaded_file.name,
                file_content=uploaded_file.read(),
            )
        raise ValueError('Request user must be required.')

    def _build_issue_detail(self, issue):
        base_detail = str(
            _("Row %(row)s · %(column)s · %(reason)s")
            % {
                "row": issue.row_number,
                "column": issue.column_label,
                "reason": str(issue.reason),
            },
        )
        guidance = self.field_input_guidance.get(issue.column_label)
        if not guidance:
            return base_detail
        return str(
            _("%(base)s Suggested format: %(guidance)s")
            % {
                "base": base_detail,
                "guidance": str(guidance),
            },
        )

    def _preview_result_rows(self, preview_rows: tuple):
        return [
            [
                (
                    (
                        json.dumps(sub_item) if isinstance(sub_item, self.preview_json_dump_type) else sub_item
                    ) if self.preview_json_dump_type else sub_item
                )
                for sub_item in list(row.values)
            ] for row in preview_rows
        ]

    def serialize_preview_result(self, preview_result):
        preview_rows = self._preview_result_rows(preview_rows=preview_result.preview_rows[:100])
        issues = [
            {
                "row_number": issue.row_number,
                "identifier": issue.identifier,
                "column_label": issue.column_label,
                "reason": str(issue.reason),
                "detail": self._build_issue_detail(issue),
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


class StudyRandomizationSchemeImportPreviewView(StudyRandomizationImportBaseView):
    preview_service_class = PreviewStudyRandomizationSchemesImportService
    preview_title = _("Randomization Scheme Preview")
    field_input_guidance = {
        "Code": _("Unique scheme code, up to 64 characters. Example: SCH-001"),
        "Name": _("Scheme name, up to 255 characters. Example: Main Scheme"),
        "Type": _("Randomization type text. Example: block"),
        "Allocation Ratio": _(
            'JSON object with ARM code as key and ratio > 0 as value. Example: {"ARM-A": 2, "ARM-B": 1}',
        ),
        "Target Randomized Total": _("Whole number greater than 0. Example: 100"),
        "Eligibility Rule Code": _("Optional rule code, up to 64 characters. Example: ELIG-01"),
        "Requires Screening Pass": _("Yes/No, True/False, or 1/0"),
        "Is Open Label": _("Yes/No, True/False, or 1/0"),
        "Status": _("One of: draft, active, closed, retried"),
        "Effective From": _("Datetime. Example: 2026-04-21 08:30"),
        "Effective To": _("Datetime and must be >= Effective From"),
        "Notes": _("Optional free text note."),
    }
    preview_json_dump_type = (dict, list)


class StudyRandomizationArmImportPreviewView(StudyRandomizationImportBaseView):
    preview_service_class = PreviewStudyRandomizationArmsImportService
    preview_title = _("Randomization Arm Preview")
    field_input_guidance = {
        "Scheme Code": _("Existing scheme code in this study. Example: SCH-001"),
        "Code": _("Unique ARM code within a scheme. Example: ARM-A"),
        "Target Count": _("Whole number greater than or equal to current assigned count"),
        "Display Order": _("Whole number used for ordering. Example: 1"),
        "Is Active": _("Yes/No, True/False, or 1/0"),
        "Notes": _("Optional free text note."),
    }


class StudyRandomizationSequencePeriodImportPreviewView(StudyRandomizationImportBaseView):
    preview_service_class = PreviewStudyRandomizationSequencePeriodsImportService
    preview_title = _("Randomization Sequence Period Preview")
    field_input_guidance = {
        "Scheme Code": _("Existing scheme code in this study. Example: NNG31_XOVER"),
        "Arm Code": _("Existing ARM code under the scheme. Example: SEQ_E_N"),
        "Period No": _("Whole number used to order treatment periods. Example: 1"),
        "Treatment Code": _("Treatment code, up to 64 characters. Example: EPREX_4000U"),
        "Start Event Code": _("Existing event code. Multiple fallback codes can be separated by /."),
        "End Event Code": _("Existing event code. Multiple fallback codes can be separated by /."),
        "Washout Days": _("Optional whole number. Leave blank or use null when not applicable."),
        "Transition Rule Code": _("Optional transition rule code. Leave blank or use null when not applicable."),
        "Display Order": _("Whole number used for ordering. Example: 1"),
    }


class StudyRandomizationCommitBaseView(StudyRandomizationImportBaseView):
    commit_service_class = None
    success_message = _("Import completed successfully.")

    def get_commit_service(self):
        return self.commit_service_class()

    def build_commit_command(self, uploaded_file):
        if self.request.user.pk and isinstance(self.request.user.pk, int):
            return to_commit_randomization_import_command(
                actor_user_id=self.request.user.pk,
                study_id=self._study.pk,
                file_name=uploaded_file.name,
                file_content=uploaded_file.read(),
            )
        raise ValueError('Request user must be required.')

    def serialize_validation_error(self, exc):
        logger.warning(
            "Randomization import validation failed with %s",
            exc.__class__.__name__,
            exc_info=(exc.__class__, exc, exc.__traceback__),
        )
        return JsonResponse(
            {
                "detail": str(_("The uploaded file contains validation issues.")),
                "issues": [
                    {
                        "row_number": issue.row_number,
                        "identifier": issue.identifier,
                        "column_label": issue.column_label,
                        "reason": str(issue.reason),
                        "detail": self._build_issue_detail(issue),
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
    field_input_guidance = StudyRandomizationSchemeImportPreviewView.field_input_guidance
    success_message = _(
        "Imported randomization schemes successfully. Created: %(created_count)s. Updated: %(updated_count)s.",
    )


class StudyRandomizationArmImportCommitView(StudyRandomizationCommitBaseView):
    commit_service_class = CommitStudyRandomizationArmsImportService
    field_input_guidance = StudyRandomizationArmImportPreviewView.field_input_guidance
    success_message = _(
        "Imported randomization arms successfully. Created: %(created_count)s. Updated: %(updated_count)s.",
    )


class StudyRandomizationSequencePeriodImportCommitView(StudyRandomizationCommitBaseView):
    commit_service_class = CommitStudyRandomizationSequencePeriodsImportService
    field_input_guidance = StudyRandomizationSequencePeriodImportPreviewView.field_input_guidance
    success_message = _(
        "Imported randomization sequence periods successfully. Created: %(created_count)s. Updated: %(updated_count)s.",
    )
