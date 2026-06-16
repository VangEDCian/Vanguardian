from django.shortcuts import redirect

from apps.identity.application.authorization import AuthorizationContext
from apps.identity.presentation.access import user_bypasses_context_permission, validate_required_context
from apps.study.public import study_site_belongs_to_study


class AuthorizationContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.authorization_context = AuthorizationContext(
            study_id=None,
            study_site_id=None,
            source="none",
            raw={},
        )
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if getattr(getattr(request, "user", None), "is_authenticated", False):
            request.authorization_context = self._resolve_context(request, view_kwargs)

        metadata = self._view_metadata(view_func)
        if metadata is None:
            return None
        if user_bypasses_context_permission(request.user):
            return validate_required_context(
                request.authorization_context,
                require_study=False,
                require_site=False,
            )
        bad_context_response = validate_required_context(
            request.authorization_context,
            require_study=metadata.get("require_study", True),
            require_site=metadata.get("require_site", False),
        )
        if (
            bad_context_response is not None
            and request.authorization_context.is_valid
            and (
                (metadata.get("require_study", True) and request.authorization_context.study_id is None)
                or (
                    metadata.get("require_site", False)
                    and request.authorization_context.study_site_id is None
                )
            )
        ):
            return redirect("/")
        if bad_context_response is not None:
            return bad_context_response
        return None

    def _resolve_context(self, request, view_kwargs) -> AuthorizationContext:
        route_values = self._route_values(view_kwargs)
        derived_route_values = self._derive_route_values(request, route_values, view_kwargs)
        if derived_route_values:
            route_values.update(derived_route_values)
        if route_values:
            return self._context_from_values("route", route_values)

        header_values = self._header_values(request)
        if self._is_api_request(request) and header_values:
            return self._context_from_values("headers", header_values)

        query_values = self._query_values(request)
        if query_values:
            return self._context_from_values("query", query_values)

        return AuthorizationContext(study_id=None, study_site_id=None, source="none", raw={})

    def _derive_route_values(self, request, route_values: dict, view_kwargs) -> dict:
        if not route_values.get("study_id") or route_values.get("study_site_id"):
            return {}

        study_id = route_values.get("study_id")
        try:
            int(study_id)
        except (TypeError, ValueError):
            return {}
        subject_id = view_kwargs.get("subject_id")
        if subject_id is not None:
            site_id = self._resolve_subject_site_id(study_id=study_id, subject_id=subject_id)
            if site_id is not None:
                return {"study_site_id": site_id}

        query_id = view_kwargs.get("query_id")
        if query_id is not None:
            site_id = self._resolve_query_site_id(study_id=study_id, query_id=query_id)
            if site_id is not None:
                return {"study_site_id": site_id}

        site_id = self._resolve_default_site_id(request=request, study_id=study_id)
        if site_id is not None:
            return {"study_site_id": site_id}

        return {}

    @staticmethod
    def _resolve_subject_site_id(*, study_id: int, subject_id: int) -> int | None:
        from apps.subject.public import get_subject_site_id

        return get_subject_site_id(
            study_id=int(study_id),
            subject_id=int(subject_id),
        )

    @staticmethod
    def _resolve_query_site_id(*, study_id: int, query_id: int) -> int | None:
        from apps.reconcile.public import get_reconcile_query_site_id

        return get_reconcile_query_site_id(
            study_id=int(study_id),
            dataquery_id=int(query_id),
        )

    @staticmethod
    def _resolve_default_site_id(*, request, study_id: int) -> int | None:
        from apps.shared.navigation import get_default_site_id

        return get_default_site_id(request, study_id=int(study_id))

    def _context_from_values(self, source: str, values: dict) -> AuthorizationContext:
        raw = dict(values)
        study_id, study_error = self._parse_int(values.get("study_id"), "study_id")
        study_site_id, study_site_error = self._parse_int(values.get("study_site_id"), "study_site_id")
        error = study_error or study_site_error
        if error:
            return AuthorizationContext(
                study_id=study_id,
                study_site_id=study_site_id,
                source=source,
                raw=raw,
                is_valid=False,
                error=error,
            )
        if study_id is not None and study_site_id is not None and not study_site_belongs_to_study(
            study_id=study_id,
            study_site_id=study_site_id,
        ):
            return AuthorizationContext(
                study_id=study_id,
                study_site_id=study_site_id,
                source=source,
                raw=raw,
                is_valid=False,
                error="study_site_id does not belong to study_id.",
            )
        return AuthorizationContext(
            study_id=study_id,
            study_site_id=study_site_id,
            source=source,
            raw=raw,
        )

    @staticmethod
    def _route_values(view_kwargs) -> dict:
        values = {}
        if "study_id" in view_kwargs:
            values["study_id"] = view_kwargs["study_id"]
        elif "study_pk" in view_kwargs:
            values["study_id"] = view_kwargs["study_pk"]

        if "study_site_id" in view_kwargs:
            values["study_site_id"] = view_kwargs["study_site_id"]
        elif "site_id" in view_kwargs:
            # Existing routes use site_id for study_site.id, not a global site id.
            values["study_site_id"] = view_kwargs["site_id"]
        return values

    @staticmethod
    def _header_values(request) -> dict:
        values = {}
        if request.headers.get("X-Study-ID"):
            values["study_id"] = request.headers.get("X-Study-ID")
        if request.headers.get("X-Study-Site-ID"):
            values["study_site_id"] = request.headers.get("X-Study-Site-ID")
        return values

    @staticmethod
    def _query_values(request) -> dict:
        values = {}
        if request.GET.get("study_id"):
            values["study_id"] = request.GET.get("study_id")
        if request.GET.get("study_site_id"):
            values["study_site_id"] = request.GET.get("study_site_id")
        return values

    @staticmethod
    def _parse_int(value, field_name: str) -> tuple[int | None, str]:
        if value in (None, ""):
            return None, ""
        try:
            return int(value), ""
        except (TypeError, ValueError):
            return None, f"Malformed {field_name} authorization context."

    @staticmethod
    def _is_api_request(request) -> bool:
        return request.path_info.startswith("/api/") or "application/json" in request.headers.get("accept", "")

    @staticmethod
    def _view_metadata(view_func):
        metadata = getattr(view_func, "context_permission_required", None)
        if metadata is not None:
            return metadata
        view_class = getattr(view_func, "view_class", None)
        if view_class is None or not getattr(view_class, "permission_required", None):
            return None
        return {
            "permission": getattr(view_class, "permission_required", ""),
            "scope": getattr(view_class, "authorization_scope", "ANY"),
            "require_study": getattr(view_class, "require_study_context", True),
            "require_site": getattr(view_class, "require_site_context", False),
        }
