from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.urls import reverse
from django.views import View

from apps.audit.public import build_audit_request_context
from apps.shared.views import AuthenticateTemplateContextMixin
from apps.study.application import (
    PreviewStudySubjectIdentifierPolicyMigrationService,
    RollbackStudySubjectIdentifierPolicyService,
    StudyAuditService,
    StudyDirectoryQueryService,
    StudyNotFoundError,
    StudySubjectIdentifierMigrationBlockedError,
    StudySubjectIdentifierMigrationRequiredError,
    StudySubjectIdentifierMigrationStalePlanError,
)
from apps.study.presentation.web.views.helpers import _user_has_study_access


class StudySubjectIdentifierPolicyAccessMixin(AuthenticateTemplateContextMixin):
    permission_required = "STUDY_CONFIG.MANAGE"
    authorization_scope = "STUDY"
    raise_exception = True
    study_directory_query_service_class = StudyDirectoryQueryService
    _study_id = None
    _study_code = None

    def dispatch(self, request, *args, **kwargs):
        unauthenticated_response = self.dispatch_authenticated(request)
        if unauthenticated_response is not None:
            return unauthenticated_response
        try:
            detail = self.study_directory_query_service_class().get_study_detail(
                study_id=kwargs["study_id"]
            )
        except StudyNotFoundError as exc:
            raise Http404 from exc
        self._study_id = kwargs["study_id"]
        self._study_code = detail["detail_study"]["code"]
        if not _user_has_study_access(request.user, self._study_id):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    @staticmethod
    def _target_values(request):
        return {
            "study_code": request.POST.get("code"),
            "subject_identifier_mode": request.POST.get("subject_identifier_mode"),
            "screening_identifier_mode": request.POST.get(
                "screening_identifier_mode"
            ),
            "subject_code_pattern": request.POST.get("subject_code_pattern"),
            "screening_code_pattern": request.POST.get("screening_code_pattern"),
            "subject_code_uniqueness_scope": request.POST.get(
                "subject_code_uniqueness_scope"
            ),
            "lock_subject_code_after_assignment": (
                request.POST.get("lock_subject_code_after_assignment")
                in {"1", "true", "True", "on", "yes"}
            ),
        }


class StudySubjectIdentifierPolicyPreviewView(
    StudySubjectIdentifierPolicyAccessMixin,
    View,
):
    service_class = PreviewStudySubjectIdentifierPolicyMigrationService

    def post(self, request, *_args, **_kwargs):
        try:
            preview = self.service_class().execute(
                study_id=self._study_id,
                target_values=self._target_values(request),
            )
        except ValueError as exc:
            return JsonResponse({"detail": str(exc)}, status=400)
        return JsonResponse(preview.as_dict())


class StudySubjectIdentifierPolicyRollbackPreviewView(
    StudySubjectIdentifierPolicyAccessMixin,
    View,
):
    service_class = RollbackStudySubjectIdentifierPolicyService

    def post(self, request, *_args, **_kwargs):
        preview = self.service_class().preview(study_id=self._study_id)
        return JsonResponse(preview.as_dict())


class StudySubjectIdentifierPolicyRollbackView(
    StudySubjectIdentifierPolicyAccessMixin,
    View,
):
    service_class = RollbackStudySubjectIdentifierPolicyService
    audit_service_class = StudyAuditService

    def post(self, request, *_args, **_kwargs):
        try:
            study, preview, before_data = self.service_class().execute(
                study_id=self._study_id,
                actor_user_id=request.user.pk,
                expected_plan_hash=request.POST.get("plan_hash"),
                confirmation_code=request.POST.get("confirmation_code"),
            )
        except (
            StudySubjectIdentifierMigrationBlockedError,
            StudySubjectIdentifierMigrationRequiredError,
            StudySubjectIdentifierMigrationStalePlanError,
        ) as exc:
            return JsonResponse(exc.preview.as_dict(), status=409)

        self.audit_service_class().record_updated(
            study=study,
            before_data=before_data,
            **build_audit_request_context(request),
        )
        return JsonResponse(
            {
                **preview.as_dict(),
                "redirect_url": reverse(
                    "study:study_detail",
                    kwargs={"study_id": self._study_id},
                ),
            }
        )


__all__ = [
    "StudySubjectIdentifierPolicyPreviewView",
    "StudySubjectIdentifierPolicyRollbackPreviewView",
    "StudySubjectIdentifierPolicyRollbackView",
]
