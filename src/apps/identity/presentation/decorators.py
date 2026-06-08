from functools import wraps

from apps.identity.presentation.access import SCOPE_ANY, enforce_context_permission


def require_context_permission(
    permission: str,
    *,
    scope: str = SCOPE_ANY,
    require_study: bool = True,
    require_site: bool = False,
):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            response = enforce_context_permission(
                request,
                permission=permission,
                scope=scope,
                require_study=require_study,
                require_site=require_site,
            )
            if response is not None:
                return response
            return view_func(request, *args, **kwargs)

        wrapped.context_permission_required = {
            "permission": permission,
            "scope": scope,
            "require_study": require_study,
            "require_site": require_site,
        }
        return wrapped

    return decorator
