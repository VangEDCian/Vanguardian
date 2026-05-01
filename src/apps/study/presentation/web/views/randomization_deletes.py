import logging

from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View

from apps.shared.views import AuthenticateTemplateContextMixin
from apps.study.application import (
    DeleteRandomizationArmCommand,
    DeleteRandomizationArmService,
    DeleteRandomizationSchemeCommand,
    DeleteRandomizationSchemeService,
    RandomizationArmNotFoundError,
    RandomizationDeleteBlockedError,
    RandomizationSchemeNotFoundError,
)
from apps.study.presentation.web.views.randomization import StudyRandomizationAccessMixin

logger = logging.getLogger(__name__)

class StudyRandomizationSchemeDeleteView(
    StudyRandomizationAccessMixin,
    AuthenticateTemplateContextMixin,
    View,
):
    permission_required = "study.update_study"
    raise_exception = True
    delete_service_class = DeleteRandomizationSchemeService

    def get_delete_service(self):
        return self.delete_service_class()

    def post(self, request, *_args, **kwargs):
        if not request.user.pk or not isinstance(request.user.pk, int):
            raise PermissionDenied

        try:
            result = self.get_delete_service().execute(
                DeleteRandomizationSchemeCommand(
                    actor_user_id=request.user.pk,
                    study_id=self._study.pk,
                    scheme_id=kwargs["scheme_id"],
                ),
            )
        except RandomizationSchemeNotFoundError as exc:
            raise Http404 from exc
        except RandomizationDeleteBlockedError as exc:
            logging.getLogger(__name__).warning(
                "Randomization scheme deletion blocked for study_id=%s scheme_id=%s",
                self._study.pk,
                kwargs.get("scheme_id"),
                exc_info=exc,
            )
            return JsonResponse(
                {"detail": str(_("Unable to delete randomization scheme."))},
                status=400,
            )

        return JsonResponse(
            {
                "detail": str(
                    _(
                        "Deleted randomization scheme successfully. Removed %(deleted_arm_count)s arm(s) and %(deleted_slot_count)s slot(s).",
                    )
                    % {
                        "deleted_arm_count": result.deleted_arm_count,
                        "deleted_slot_count": result.deleted_slot_count,
                    }
                ),
                "redirect_url": reverse(
                    "study:study_randomization",
                    kwargs={"study_id": self._study.pk},
                ),
            },
        )


class StudyRandomizationArmDeleteView(
    StudyRandomizationAccessMixin,
    AuthenticateTemplateContextMixin,
    View,
):
    permission_required = "study.update_study"
    raise_exception = True
    delete_service_class = DeleteRandomizationArmService

    def get_delete_service(self):
        return self.delete_service_class()

    def post(self, request, *_args, **kwargs):
        if not request.user.pk or not isinstance(request.user.pk, int):
            raise PermissionDenied

        try:
            result = self.get_delete_service().execute(
                DeleteRandomizationArmCommand(
                    actor_user_id=request.user.pk,
                    study_id=self._study.pk,
                    arm_id=kwargs["arm_id"],
                ),
            )
        except RandomizationArmNotFoundError as exc:
            raise Http404 from exc
        except RandomizationDeleteBlockedError as exc:
            logger.warning(
                "Randomization arm deletion blocked for study_id=%s arm_id=%s user_id=%s",
                self._study.pk,
                kwargs.get("arm_id"),
                request.user.pk,
                exc_info=exc,
            )
            return JsonResponse(
                {"detail": str(_("Unable to delete randomization arm."))},
                status=400,
            )

        return JsonResponse(
            {
                "detail": str(
                    _(
                        "Deleted randomization arm successfully. Removed %(deleted_slot_count)s slot(s).",
                    )
                    % {"deleted_slot_count": result.deleted_slot_count}
                ),
                "redirect_url": reverse(
                    "study:study_randomization",
                    kwargs={"study_id": self._study.pk},
                ),
            },
        )
