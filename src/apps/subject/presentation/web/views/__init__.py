"""Subject web views package.

``SubjectDetailView`` is loaded lazily so importing ``views.base`` (e.g. from
``apps.subject.public``) does not pull in ``detail`` and avoids cycles with
``apps.datacapture.public``.
"""

from apps.subject.presentation.web.views.base import SubjectAbstractVerifyStudy
from apps.subject.presentation.web.views.create import SubjectCreateView
from apps.subject.presentation.web.views.event_instance_files import (
    SubjectEventInstanceFileContentView,
    SubjectEventInstanceFileImportView,
    SubjectEventInstanceFilePreviewView,
)
from apps.subject.presentation.web.views.listing import SubjectListView
from apps.subject.presentation.web.views.repeating_event_instance import (
    SubjectAddRepeatingEventInstanceView,
)

__all__ = [
    "SubjectAddRepeatingEventInstanceView",
    "SubjectAbstractVerifyStudy",
    "SubjectCreateView",
    "SubjectEventInstanceFileContentView",
    "SubjectEventInstanceFileImportView",
    "SubjectEventInstanceFilePreviewView",
    "SubjectDetailView",
    "SubjectListView",
]


def __getattr__(name: str):
    if name == "SubjectDetailView":
        from apps.subject.presentation.web.views.detail import SubjectDetailView

        return SubjectDetailView
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
