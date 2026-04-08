from django.http import HttpResponse

from apps.shared.context_processors import (
    StudyDropdownHandler, SiteDropdownHandler,
)


class CookiesService:
    @classmethod
    def reset_cookies(cls, response: HttpResponse):
        study_state = StudyDropdownHandler.destroy_cookie(response=response)
        site_state = SiteDropdownHandler.destroy_cookie(response=response)
        return study_state and site_state
