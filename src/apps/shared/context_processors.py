__all__ = [
    'StudyDropdownHandler',
    'SiteDropdownHandler',
    'shared_select_options',
]

import abc
from dataclasses import dataclass, field

from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.utils.translation import gettext_lazy as _

from apps.identity.infrastructure.persistence.models import StudyMembership
from apps.identity.infrastructure.persistence.models import StudySiteMembership

from apps.study.infrastructure.persistence.models import Study, Site


@dataclass
class DropdownData:
    selected_id: int = None
    select_options: list[dict] = field(default_factory=list)
    select_display_text: str = _("Select study")


class DropdownHandlerAbstract(abc.ABC):
    """
    Base handler for building dropdown data from request context.

    This abstract class centralizes:
    - reading/writing selected values via browser cookies (`COOKIE_NAME`)
    - resolving authenticated user from the incoming request
    - transforming model objects into `DropdownData` for templates

    Subclasses must implement `get_objects()` and return items exposing
    `id` and `code` attributes for dropdown option mapping.

    The `build()` method reads selected id from cookie, computes selected
    option/display text, and safely falls back to an empty `DropdownData`
    for anonymous users or unexpected errors.
    """
    COOKIE_NAME = ""
    PLACEHOLDER_TEXT = _("Select option")

    def __init__(self, request: HttpRequest, **kwargs):
        """Initialize handler state from the current HTTP request.

        Stores the request object and resolves `self.user` to the authenticated
        user. If the request user is missing or anonymous, `self.user` is set
        to `None`.
        """
        self.request = request
        self.user = request.user if request.user and request.user.is_authenticated else None

    def get_cookie_value(self, parse_to_int: bool = True):
        """Return current selected value from the dropdown cookie.

        Args:
            parse_to_int: Convert cookie value to `int` when `True`.

        Returns:
            The cookie value, parsed as `int` when requested and valid;
            otherwise the raw string value or `None` when absent/invalid.
        """
        idx = self.request.COOKIES.get(self.COOKIE_NAME, None)
        if idx is not None:
            if parse_to_int:
                try:
                    idx = int(idx)
                except ValueError:
                    idx = None
        return idx

    def set_cookie_value(self, value):
        """Set the selected dropdown value in request cookies.

        This updates the in-request cookie mapping under `COOKIE_NAME`.

        Args:
            value: Value to store for the dropdown selection.

        Returns:
            Always returns `True`.
        """
        self.request.COOKIES[self.COOKIE_NAME] = value
        return True

    @classmethod
    def destroy_cookie(cls, response: HttpResponse) -> bool:
        try:
            response.delete_cookie(cls.COOKIE_NAME)
            return True
        except Exception:
            pass
        return False

    def get_objects(self) -> QuerySet:
        """Return selectable objects for the dropdown.

        Subclasses must implement this and return a queryset/iterable of
        objects exposing `id` and `code` attributes, which are consumed by
        `build()` to generate option values and labels.
        """
        raise NotImplementedError()

    def build(self) -> DropdownData:
        """Build and return dropdown data for template rendering.

        For authenticated users, this method reads the selected id from cookie,
        loads selectable objects from `get_objects()`, marks the selected
        option, and resolves display text to the selected object's `code` or
        `PLACEHOLDER_TEXT`.

        Returns:
            A populated `DropdownData` when possible; otherwise a default empty
            `DropdownData` for anonymous users or unexpected errors.
        """
        if self.user:
            try:
                study_selected_id = self.get_cookie_value(parse_to_int=True)
                study_objs = list(self.get_objects())

                if study_objs and not any(obj.id == study_selected_id for obj in study_objs):
                    study_selected_id = study_objs[0].id

                select_display_text = self.PLACEHOLDER_TEXT
                for obj in study_objs:
                    if study_selected_id == obj.id:
                        select_display_text = obj.code
                        break

                return DropdownData(
                    selected_id=study_selected_id,
                    select_options=[
                        {
                            "value": str(obj.id),
                            "label": obj.code,
                            "selected": study_selected_id == obj.id,
                        } for obj in study_objs
                    ],
                    select_display_text=select_display_text,
                )
            except Exception:
                pass
        return DropdownData()


class StudyDropdownHandler(DropdownHandlerAbstract):
    COOKIE_NAME = "study_dropdown"
    PLACEHOLDER_TEXT = _("Select study")

    def get_objects(self):
        qs = Study.objects.only('id', 'code').filter(is_active=True, deleted=False)

        # Only Django superusers bypass membership filtering.
        if not self.user.is_superuser:
            belong_to_studies = StudyMembership.objects.filter(
                user=self.user, deleted=False,
            ).values_list(
                "study_id", flat=True,
            )
            qs = qs.filter(pk__in=belong_to_studies)

        return qs.order_by("id")


class SiteDropdownHandler(StudyDropdownHandler):
    COOKIE_NAME = "site_dropdown"
    PLACEHOLDER_TEXT = _("Select site")

    def __init__(self, request: HttpRequest, study_id: int or None, **kwargs):
        self.study_id = study_id
        super().__init__(request, **kwargs)

    def get_objects(self):
        qs = Site.objects.only('id', 'code').filter(
            study_id=self.study_id, is_active=True, deleted=False,
        )

        # Only Django superusers bypass membership filtering.
        if not self.user.is_superuser:
            belong_to_studies = StudySiteMembership.objects.filter(
                user=self.user, deleted=False,
            ).values_list("site_id", flat=True)
            qs = qs.filter(pk__in=belong_to_studies)

        return qs.order_by("id")


def shared_select_options(request):
    study_dd = StudyDropdownHandler(request=request).build()
    site_dd = SiteDropdownHandler(request=request, study_id=study_dd.selected_id).build()
    return {
        # study
        "shared_study_cookies_key": StudyDropdownHandler.COOKIE_NAME,
        "shared_study_selected_id": study_dd.selected_id,
        "shared_study_select_default": study_dd.select_display_text,
        "shared_study_select_options": study_dd.select_options,

        # site
        "shared_site_cookies_key": SiteDropdownHandler.COOKIE_NAME,
        "shared_site_selected_id": site_dd.selected_id,
        "shared_site_select_default": site_dd.select_display_text,
        "shared_site_select_options": site_dd.select_options,

        # another
        "shared_language_select_options": [
            {"value": "vi", "label": _("Vietnamese")},
            {"value": "en", "label": _("English")},
        ],
    }
