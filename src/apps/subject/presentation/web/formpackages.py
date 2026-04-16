from django.utils.translation import gettext_lazy as _

from apps.shared.filters import SharedSearch, SharedTotal
from apps.subject.models import Subject

__all__ = ["SubjectsToolbarForm"]


class SubjectsToolbarForm(SharedSearch, SharedTotal):
    SEARCH_FIELDS = ("subject_code", "screening_code")
    TOTAL_LABEL = _("Total Subjects")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bind_total_field()

    class Meta:
        model = Subject
        fields = ("search",)
        toolbar_fields = ("total", "search")
