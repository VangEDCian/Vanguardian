from django.urls import reverse

from apps.core.choices import DataCapturePageStateStatusChoices
from apps.datacapture.public import get_page_state_status_for_subject_visit_crf


class SubjectFormVerificationNavigationService:

    @staticmethod
    def filter_submitted_only(*, subject_id: int, event_navigation: list) -> list:
        out: list = []
        for event_item in event_navigation or []:
            try:
                visit_id = int(event_item["id"])
            except (TypeError, ValueError):
                continue
            forms_out = []
            for form_item in event_item.get("forms") or []:
                try:
                    crf_template_id = int(form_item.get("form_definition_id") or "")
                except (TypeError, ValueError):
                    continue
                status = get_page_state_status_for_subject_visit_crf(
                    subject_id=subject_id,
                    visit_id=visit_id,
                    crf_template_id=crf_template_id,
                )
                if status == DataCapturePageStateStatusChoices.SUBMITTED:
                    forms_out.append(form_item)
            if forms_out:
                out.append({**event_item, "forms": forms_out})
        return out

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
