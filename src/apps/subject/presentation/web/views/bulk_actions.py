import logging

from django.contrib import messages
from django.http import HttpResponse, QueryDict
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import content_disposition_header, url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views import View

from apps.audit.public import build_audit_request_context
from apps.shared.views import AuthenticateTemplateContextMixin
from apps.subject.application.services.bulk_actions import SubjectBulkActionService
from apps.subject.application.services.excel_export import (
    EXCEL_CONTENT_TYPE,
    SubjectExcelExportSelectionError,
    SubjectExcelExportService,
)
from apps.subject.presentation.web.forms import (
    SubjectBulkActionForm,
    SubjectEarlyTerminationForm,
    SubjectExcelExportForm,
    SubjectsToolbarForm,
)
from apps.subject.presentation.web.mappers.subject_list_model import (
    get_subject_list_row_model,
)
from apps.subject.presentation.web.views.base import SubjectAbstractVerifyStudy

logger = logging.getLogger(__name__)


class SubjectBulkActionView(
    AuthenticateTemplateContextMixin,
    SubjectAbstractVerifyStudy,
    View,
):
    authorization_scope = "STUDY_SITE"
    require_site_context = True
    raise_exception = True
    service_class = SubjectBulkActionService
    excel_export_service_class = SubjectExcelExportService
    permission_by_action = {
        SubjectBulkActionForm.ACTION_DELETE: "subject.delete_subject",
        SubjectBulkActionForm.ACTION_RESYNC_STAGE: "SUBJECT.UPDATE",
        SubjectBulkActionForm.ACTION_EARLY_TERMINATE: "SUBJECT.EARLY_TERMINATE",
        SubjectBulkActionForm.ACTION_EXPORT_EXCEL: "DATA_EXPORT.RUN",
    }
    invalid_action_permission = "subject.invalid_bulk_action"

    def get_permission_required(self):
        action = (self.request.POST.get("action") or "").strip()
        return (self.permission_by_action.get(action, self.invalid_action_permission),)

    def post(self, request, *args, **kwargs):
        study_id = kwargs["study_id"]
        site_id = self.get_permission_authorization_context().study_site_id
        next_url = self._resolve_next_url(request, study_id=study_id)
        selection_form = SubjectBulkActionForm(request.POST)
        if not selection_form.is_valid():
            messages.error(request, _("Bulk action was not run. Select at least one valid subject."))
            return redirect(next_url)

        action = selection_form.cleaned_data["action"]
        subject_ids = self._resolve_subject_ids(
            study_id=study_id,
            selection_form=selection_form,
        )
        if not subject_ids:
            messages.error(
                request,
                _("Bulk action was not run. The current filter has no subjects."),
            )
            return redirect(next_url)
        if action == SubjectBulkActionForm.ACTION_EXPORT_EXCEL:
            return self._export_subjects(
                request=request,
                study_id=study_id,
                site_id=site_id,
                subject_ids=subject_ids,
                next_url=next_url,
            )
        service = self.service_class()
        try:
            if action == SubjectBulkActionForm.ACTION_DELETE:
                result = service.delete_subjects(
                    study_id=study_id,
                    site_id=site_id,
                    subject_ids=subject_ids,
                    **build_audit_request_context(request),
                )
            elif action == SubjectBulkActionForm.ACTION_RESYNC_STAGE:
                result = service.resync_subjects(
                    study_id=study_id,
                    site_id=site_id,
                    subject_ids=subject_ids,
                    actor_user_id=request.user.pk,
                )
            else:
                termination_form = SubjectEarlyTerminationForm(request.POST)
                if not termination_form.is_valid():
                    messages.error(
                        request,
                        _("Early termination was not started. Complete all required fields."),
                    )
                    return redirect(next_url)
                result = service.start_early_termination(
                    study_id=study_id,
                    site_id=site_id,
                    subject_ids=subject_ids,
                    actor_user_id=request.user.pk,
                    effective_at=termination_form.cleaned_data["effective_at"],
                    reason_code=termination_form.cleaned_data["reason_code"],
                    reason_text=termination_form.cleaned_data["reason_text"],
                )
        except Exception:
            logger.exception(
                "Subject bulk action failed: action=%s study_id=%s site_id=%s "
                "subject_ids=%s user_id=%s",
                action,
                study_id,
                site_id,
                subject_ids,
                request.user.pk,
            )
            messages.error(request, _("Bulk action failed. Please check the server log for details."))
            return redirect(next_url)

        logger.info(
            "Subject bulk action result: action=%s study_id=%s site_id=%s "
            "selected=%s scoped=%s succeeded=%s skipped=%s out_of_scope=%s "
            "reasons=%s user_id=%s",
            action,
            study_id,
            site_id,
            result.selected_count,
            result.scoped_count,
            result.succeeded_count,
            result.skipped_count,
            result.out_of_scope_count,
            result.reason_counts,
            request.user.pk,
        )
        self._add_result_message(request, action=action, result=result)
        return redirect(next_url)

    def _export_subjects(
        self,
        *,
        request,
        study_id: int,
        site_id: int,
        subject_ids: tuple[int, ...],
        next_url: str,
    ):
        export_form = SubjectExcelExportForm(request.POST)
        if not export_form.is_valid():
            messages.error(
                request,
                _("Excel export was not run. Select at least one valid field."),
            )
            return redirect(next_url)
        try:
            result = self.excel_export_service_class().export(
                study_id=study_id,
                site_id=site_id,
                subject_ids=subject_ids,
                selected_field_tokens=export_form.cleaned_data["export_fields"],
            )
        except SubjectExcelExportSelectionError as exc:
            messages.error(request, str(exc))
            return redirect(next_url)
        except Exception:
            logger.exception(
                "Subject Excel export failed: study_id=%s site_id=%s "
                "subject_ids=%s user_id=%s",
                study_id,
                site_id,
                subject_ids,
                request.user.pk,
            )
            messages.error(
                request,
                _("Excel export failed. Please check the server log for details."),
            )
            return redirect(next_url)

        logger.info(
            "Subject Excel export result: study_id=%s site_id=%s "
            "subjects=%s fields=%s user_id=%s",
            study_id,
            site_id,
            result.subject_count,
            result.field_count,
            request.user.pk,
        )
        response = HttpResponse(
            result.content,
            content_type=EXCEL_CONTENT_TYPE,
        )
        response["Content-Disposition"] = content_disposition_header(
            True,
            result.filename,
        )
        return response

    @staticmethod
    def _resolve_subject_ids(
        *,
        study_id: int,
        selection_form: SubjectBulkActionForm,
    ) -> tuple[int, ...]:
        if (
            selection_form.cleaned_data["selection_mode"]
            != SubjectBulkActionForm.SELECTION_FILTERED
        ):
            return selection_form.cleaned_data["subject_ids"]

        filter_params = QueryDict(
            selection_form.cleaned_data.get("filter_query", ""),
        )
        queryset = get_subject_list_row_model().objects.filter(
            study_id=study_id,
            deleted=False,
        )
        filtered_queryset = SubjectsToolbarForm(
            filter_params,
            queryset=queryset,
        ).qs
        return tuple(
            filtered_queryset.order_by("pk").values_list("pk", flat=True)
        )

    @staticmethod
    def _add_result_message(request, *, action: str, result):
        if action == SubjectBulkActionForm.ACTION_DELETE:
            if result.succeeded_count:
                messages.success(
                    request,
                    _("Deleted %(count)s selected subjects.")
                    % {"count": result.succeeded_count},
                )
            else:
                messages.warning(request, _("No selected subjects were deleted."))
        elif action == SubjectBulkActionForm.ACTION_RESYNC_STAGE:
            resync = result.resync_result
            if resync is None or not resync.study_version:
                messages.warning(
                    request,
                    _("Resync stage did not run: %(reason)s.")
                    % {"reason": getattr(resync, "reason", "subjects_not_found")},
                )
            else:
                messages.success(
                    request,
                    _(
                        "Resynced %(count)s subjects. Created: %(created)s, "
                        "updated: %(updated)s, impacts: %(impacts)s."
                    )
                    % {
                        "count": result.succeeded_count,
                        "created": resync.created_count,
                        "updated": resync.updated_count,
                        "impacts": resync.impact_flag_count,
                    },
                )
        else:
            if result.succeeded_count:
                messages.success(
                    request,
                    _("Started early termination for %(count)s selected subjects.")
                    % {"count": result.succeeded_count},
                )
            else:
                messages.warning(
                    request,
                    _("Early termination was not started for any selected subjects."),
                )

        if result.skipped_count or result.out_of_scope_count:
            messages.warning(
                request,
                _(
                    "Skipped %(skipped)s subjects; %(out_of_scope)s were outside "
                    "the selected study site."
                )
                % {
                    "skipped": result.skipped_count,
                    "out_of_scope": result.out_of_scope_count,
                },
            )

    @staticmethod
    def _resolve_next_url(request, *, study_id: int) -> str:
        next_url = (request.POST.get("next") or "").strip()
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return next_url
        return reverse("subject:subject_list", kwargs={"study_id": study_id})


__all__ = ["SubjectBulkActionView"]
