from django.urls import reverse


class SubjectFormVerificationNavigationService:

    @staticmethod
    def filter_submitted_only(*, subject_id: int, event_navigation: list) -> list:
        _ = subject_id
        return list(event_navigation or [])

    @staticmethod
    def first_verification_url(*, study_id: int, subject_id: int, event_navigation_submitted: list) -> str | None:
        if not event_navigation_submitted:
            return None
        first_event = event_navigation_submitted[0]
        forms = first_event.get("forms") or []
        if not forms:
            return None
        first_form = forms[0]
        base = reverse(
            "subject:subject_detail",
            kwargs={"study_id": study_id, "subject_id": subject_id},
        )
        return f"{base}?mode=verification&event={first_event['id']}&form={first_form['id']}"
