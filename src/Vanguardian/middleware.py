from django.conf import settings
from django.contrib import messages
from django.utils.translation import gettext as _


class SearchEngineControlMiddleware:
    AUTH_PATH_PREFIXES = (
        "/login/",
        "/itsnotasignin/",
        "/forgot-password/",
        "/reset-password/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if getattr(settings, "SEARCH_ENGINE_INDEXING_ENABLED", False):
            return response

        response.headers.setdefault(
            "X-Robots-Tag",
            getattr(settings, "SEARCH_ENGINE_ROBOTS_POLICY", "noindex, nofollow, noarchive"),
        )

        if any(request.path_info.startswith(prefix) for prefix in self.AUTH_PATH_PREFIXES):
            response.headers.setdefault("Cache-Control", "no-store, no-cache, max-age=0, must-revalidate")

        return response


class TemplateMutationFeedbackMiddleware:
    SUPPORTED_METHODS = {"POST", "PUT", "DELETE"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.method not in self.SUPPORTED_METHODS:
            return response
        if self._is_api_request(request, response):
            return response
        if self._has_existing_messages(request):
            return response

        if self._is_success_response(response):
            messages.success(request, _("The operation completed successfully."))
        else:
            messages.error(request, _("The operation failed. Please review the data and try again."))

        return response

    @staticmethod
    def _is_api_request(request, response):
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return True

        path = request.path_info or ""
        if path.startswith("/datacapture/"):
            return True
        if path.startswith("/api/") or "/api/" in path:
            return True

        resolver_match = getattr(request, "resolver_match", None)
        url_name = getattr(resolver_match, "url_name", "") or ""
        if url_name.startswith("api_"):
            return True

        return False

    @staticmethod
    def _has_existing_messages(request):
        storage = getattr(request, "_messages", None)
        if storage is None:
            return False

        queued_messages = getattr(storage, "_queued_messages", ())
        loaded_messages = getattr(storage, "_loaded_messages", ())
        return bool(queued_messages or loaded_messages)

    @staticmethod
    def _is_success_response(response):
        status_code = response.status_code
        if 300 <= status_code < 400:
            return True
        return status_code in {201, 202, 204}
