from django.http import Http404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.shared.views import AuthenticateTemplateView
from apps.subject.application.services.subject_summary import SubjectSummaryQueryService
from apps.subject.presentation.web.views.base import SubjectAbstractVerifyStudy


class SubjectSummaryView(
    AuthenticateTemplateView,
    SubjectAbstractVerifyStudy,
):
    permission_required = "subject.view_subject_detail"
    authorization_scope = "STUDY_SITE"
    require_site_context = True
    raise_exception = True
    layout_nav_key = "SUBJECTS"
    template_name = "subject/subject_summary.html"
    service_class = SubjectSummaryQueryService
    summary_model = None

    def get_service(self):
        return self.service_class()

    def get_summary_model(self):
        if self.summary_model is None:
            self.summary_model = self.get_service().get_subject_summary(
                study_id=self.get_study_id(),
                subject_id=self.kwargs["subject_id"],
            )
        if self.summary_model is None:
            raise Http404
        return self.summary_model

    def get_layout_breadcrumb_label(self):
        summary = self.get_summary_model()
        return summary["subject_code"] or summary["screening_code"] or _("SUBJECT SUMMARY")

    def get_layout_detail_meta_items(self):
        summary = self.get_summary_model()
        return (
            {
                "label": _("Site"),
                "value": summary["site_code"],
            },
            {
                "label": _("Subject ID"),
                "value": summary["subject_code"] or summary["screening_code"] or "—",
            },
            {
                "label": _("Study"),
                "value": summary["study_code"],
            },
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        summary = self.get_summary_model()
        summary["back_url"] = self._resolve_back_url()
        summary["audit_history_url"] = reverse(
            "subject:subject_audit_history",
            kwargs={"study_id": self.get_study_id(), "subject_id": self.kwargs["subject_id"]},
        )
        context["subject_summary"] = summary
        return context

    def _resolve_back_url(self) -> str:
        next_url = (self.request.GET.get("next") or "").strip()
        if next_url.startswith("/"):
            return next_url
        return reverse("subject:subject_list", kwargs={"study_id": self.get_study_id()})


__all__ = ["SubjectSummaryView"]
