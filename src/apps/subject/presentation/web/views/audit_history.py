from django.http import Http404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_tables2.views import RequestConfig

from apps.shared.views import AuthenticateTemplateView
from apps.subject.application.services.audit_history import SubjectAuditHistoryQueryService
from apps.subject.presentation.web.forms import SubjectAuditHistoryFilterForm
from apps.subject.presentation.web.tables import SubjectAuditHistoryTable
from apps.subject.presentation.web.views.base import SubjectAbstractVerifyStudy


class SubjectAuditHistoryView(
    AuthenticateTemplateView,
    SubjectAbstractVerifyStudy,
):
    permission_required = "subject.view_subject_detail"
    authorization_scope = "STUDY_SITE"
    require_site_context = True
    raise_exception = True
    layout_nav_key = "SUBJECTS"
    template_name = "subject/subject_audit_history.html"
    service_class = SubjectAuditHistoryQueryService
    filter_form_class = SubjectAuditHistoryFilterForm
    table_class = SubjectAuditHistoryTable
    paginate_by = 25
    audit_history = None
    filter_form = None

    def get_service(self):
        return self.service_class()

    def get_audit_history(self):
        if self.audit_history is None:
            filter_form = self.get_filter_form()
            cleaned = filter_form.cleaned_data
            self.audit_history = self.get_service().get_subject_audit_history(
                study_id=self.get_study_id(),
                subject_id=self.kwargs["subject_id"],
                search=cleaned.get("search") or "",
                field_name=cleaned.get("field_name") or "",
            )
        if self.audit_history is None:
            raise Http404
        return self.audit_history

    def get_filter_form(self):
        if self.filter_form is None:
            self.filter_form = self.filter_form_class(self.request.GET.copy())
            self.filter_form.is_valid()
        return self.filter_form

    def get_layout_breadcrumb_label(self):
        audit_history = self.get_audit_history()
        return audit_history["subject_code"] or audit_history["screening_code"] or _("AUDIT HISTORY")

    def get_layout_detail_meta_items(self):
        audit_history = self.get_audit_history()
        return (
            {
                "label": _("Site"),
                "value": audit_history["site_code"],
            },
            {
                "label": _("Subject ID"),
                "value": audit_history["subject_code"] or audit_history["screening_code"] or "—",
            },
            {
                "label": _("Study"),
                "value": audit_history["study_code"],
            },
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        audit_history = self.get_audit_history()
        filter_form = self.get_filter_form()
        table = self.table_class(audit_history["records"])
        table.empty_text = _("No audit history matches the current filters.")
        RequestConfig(self.request, paginate={"per_page": self.paginate_by}).configure(table)
        audit_history["back_url"] = self._resolve_back_url()
        audit_history["subject_detail_url"] = reverse(
            "subject:subject_detail",
            kwargs={"study_id": self.get_study_id(), "subject_id": self.kwargs["subject_id"]},
        )
        context["subject_audit_history"] = audit_history
        context["filter_form"] = filter_form
        context["table"] = table
        return context

    def _resolve_back_url(self) -> str:
        next_url = (self.request.GET.get("next") or "").strip()
        if next_url.startswith("/"):
            return next_url
        return reverse(
            "subject:subject_detail",
            kwargs={"study_id": self.get_study_id(), "subject_id": self.kwargs["subject_id"]},
        )


__all__ = ["SubjectAuditHistoryView"]
