from django.contrib.auth.mixins import AccessMixin

from apps.identity.presentation.access import SCOPE_ANY, enforce_context_permission


class ContextPermissionRequiredMixin(AccessMixin):
    permission_required: str = ""
    authorization_scope: str = SCOPE_ANY
    require_study_context: bool = True
    require_site_context: bool = False

    def dispatch(self, request, *args, **kwargs):
        # This must run before the handler to prevent protected EDC business
        # actions from executing without a study/site-scoped decision.
        response = enforce_context_permission(
            request,
            permission=self.permission_required,
            scope=self.authorization_scope,
            require_study=self.require_study_context,
            require_site=self.require_site_context,
        )
        if response is not None:
            return response
        return super().dispatch(request, *args, **kwargs)
