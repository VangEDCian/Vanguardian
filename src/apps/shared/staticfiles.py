from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import StaticFilesStorage


class VersionedStaticFilesStorage(StaticFilesStorage):
    """Append a file-mtime version query to Django static asset URLs."""

    version_query_key = "v"

    def url(self, name, *args, **kwargs):
        url = super().url(name, *args, **kwargs)
        version = self._asset_version(name)
        if not version:
            return url

        parts = urlsplit(url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query[self.version_query_key] = version
        return urlunsplit(
            (
                parts.scheme,
                parts.netloc,
                parts.path,
                urlencode(query),
                parts.fragment,
            )
        )

    def _asset_version(self, name) -> str:
        path = self._resolve_static_path(name)
        if path is None:
            return ""
        try:
            return str(path.stat().st_mtime_ns)
        except OSError:
            return ""

    def _resolve_static_path(self, name) -> Path | None:
        try:
            storage_path = Path(self.path(name))
            if storage_path.exists():
                return storage_path
        except (NotImplementedError, OSError, ValueError):
            pass

        finder_path = finders.find(name)
        if isinstance(finder_path, (list, tuple)):
            finder_path = finder_path[0] if finder_path else None
        return Path(finder_path) if finder_path else None
