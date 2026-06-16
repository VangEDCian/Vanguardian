from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.views import View

from apps.study.application.services import StudySiteDirectoryQueryService
from apps.study.presentation.web.views.helpers import _user_has_study_access


class SubjectAbstractVerifyStudy(View):
    study_obj = None

    def get_study_id(self):
        return self.kwargs["study_id"]

    def dispatch(self, request, *args, **kwargs):
        study_id = self.get_study_id()
        self.study_obj = StudySiteDirectoryQueryService.get_study_id(study_id=study_id)
        if self.study_obj:
            if not _user_has_study_access(request.user, study_id):
                raise PermissionDenied
            return super().dispatch(request, *args, **kwargs)
        raise Http404
