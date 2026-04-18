from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, ListView
from django_filters.views import FilterView
from django_tables2 import SingleTableMixin

from apps.shared.context_processors import StudyDropdownHandler, SiteDropdownHandler
from apps.shared.views import AuthenticateTemplateContextMixin
from apps.core.choices.study import EventInstanceStatusChoices
from apps.study.application.queries.site_directory import StudySiteDirectoryQueryService
from apps.study.models import EventFormBinding
from apps.study.presentation.web.viewpackages._helpers import _user_has_study_access
from apps.subject.application.commands.create_subject import (
    CreateSubjectCommand,
    CreateSubjectService,
)
from apps.subject.models import Subject, SubjectEventInstance
from apps.subject.presentation.web.formpackages import SubjectsToolbarForm
from apps.subject.presentation.web.tables import SubjectListTable

__all__ = ["SubjectListView", "SubjectDetailView", "SubjectCreateView"]


class SubjectAbstractVerifyStudy(View):
    study_obj = None

    def get_study_id(self):
        return self.kwargs["study_id"]

    def dispatch(self, request, *args, **kwargs):
        study_id = self.get_study_id()
        self.study_obj = StudySiteDirectoryQueryService.get_study_id(study_id=study_id)
        if self.study_obj:
            if not _user_has_study_access(request.user, study_id):
                raise PermissionDenied
            return super().dispatch(request, *args, **kwargs)
        raise Http404


class SubjectListView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuthenticateTemplateContextMixin,
    SingleTableMixin,
    FilterView,
    ListView,
    SubjectAbstractVerifyStudy,
):
    permission_required = "subject.view_subject_list"
    raise_exception = True
    layout_nav_key = "SUBJECTS"
    layout_breadcrumb_label = _("SUBJECTS")

    model = Subject
    template_name = "subject/subjects.html"
    table_class = SubjectListTable
    filterset_class = SubjectsToolbarForm
    paginate_by = 25

    @staticmethod
    def _get_resolved_study_id(request):
        return StudyDropdownHandler(request=request).build().selected_id

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(study_id=self.get_study_id(), deleted=False)
            .select_related("site", "study", "enrollment", "randomization")
            .order_by("current_sequence", "id")
        )

    def get(self, request, *args, **kwargs):
        path_study_id = self.get_study_id()
        resolved_study_id = self._get_resolved_study_id(request)
        if path_study_id and resolved_study_id:
            if path_study_id == resolved_study_id:
                return super().get(request, *args, **kwargs)
            return redirect(
                reverse(
                    "subject:subject_list",
                    kwargs={"study_id": resolved_study_id},
                )
            )
        return redirect(reverse("dashboard:main"))


class SubjectDetailView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuthenticateTemplateContextMixin,
    DetailView,
    SubjectAbstractVerifyStudy,
):
    permission_required = "subject.view_subject_detail"
    raise_exception = True
    layout_nav_key = "SUBJECTS"
    template_name = "subject/subject_detail.html"

    model = Subject
    pk_url_kwarg = "subject_id"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(study_id=self.get_study_id(), deleted=False)
            .select_related("site", "study")
        )

    def get_layout_show_breadcrumb_trail(self):
        return False

    def get_layout_breadcrumb_label(self):
        subject = getattr(self, "object", None)
        if subject is None:
            return super().get_layout_breadcrumb_label()
        return subject.subject_code or subject.screening_code or _("SUBJECT DETAIL")

    def get_layout_detail_meta_items(self):
        subject = getattr(self, "object", None)
        if subject is None:
            return super().get_layout_detail_meta_items()

        return (
            {
                "label": _("Site"),
                "value": subject.site.code,
            },
            {
                "label": _("Subject ID"),
                "value": subject.subject_code or subject.screening_code or "—",
            },
            {
                "label": _("Study"),
                "value": subject.study.code,
            },
        )

    def _build_event_navigation(self):
        event_instances = list(
            SubjectEventInstance.objects.filter(
                subject_id=self.object.pk,
                deleted=False,
            )
            .exclude(status=EventInstanceStatusChoices.NOT_READY)
            .select_related("event_definition")
            .order_by("event_definition__sequence_no", "repeat_index", "id")
        )

        event_definition_ids = [item.event_definition_id for item in event_instances]
        bindings = list(
            EventFormBinding.objects.filter(
                study_id=self.object.study_id,
                deleted=False,
                is_enabled=True,
                event_definition_id__in=event_definition_ids,
            )
            .select_related("form_definition")
            .prefetch_related("form_definition__translations")
            .order_by("event_definition__sequence_no", "display_order", "id")
        )

        bindings_map = {}
        for binding in bindings:
            bindings_map.setdefault(binding.event_definition_id, []).append(binding)

        payload = []
        for event_instance in event_instances:
            forms = []
            for binding in bindings_map.get(event_instance.event_definition_id, []):
                template = binding.form_definition
                template_name = template.safe_translation_getter(
                    "name",
                    default=template.code,
                    any_language=True,
                )
                forms.append(
                    {
                        "id": str(binding.pk),
                        "title": template_name,
                        "code": template.code,
                    }
                )

            payload.append(
                {
                    "id": str(event_instance.pk),
                    "code": event_instance.event_code_snapshot or event_instance.event_definition.code,
                    "name": event_instance.event_name_snapshot or event_instance.event_definition.name,
                    "status": event_instance.status,
                    "forms": forms,
                }
            )
        return payload

    @staticmethod
    def _resolve_focus(items, focus_id):
        if not items:
            return None
        for item in items:
            if item["id"] == focus_id:
                return item
        return items[0]

    def _with_focus_urls(self, event_navigation):
        detail_url = reverse(
            "subject:subject_detail",
            kwargs={
                "study_id": self.get_study_id(),
                "subject_id": self.object.pk,
            },
        )
        payload = []
        for event_item in event_navigation:
            forms_with_url = [
                {
                    **form_item,
                    "focus_url": f"{detail_url}?event={event_item['id']}&form={form_item['id']}",
                }
                for form_item in event_item["forms"]
            ]
            payload.append(
                {
                    **event_item,
                    "focus_url": f"{detail_url}?event={event_item['id']}",
                    "forms": forms_with_url,
                },
            )
        return payload

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subject = self.object
        event_navigation = self._with_focus_urls(self._build_event_navigation())

        focus_event_id = (self.request.GET.get("event") or "").strip()
        focused_event = self._resolve_focus(event_navigation, focus_event_id)
        focused_forms = focused_event["forms"] if focused_event else []

        focus_form_id = (self.request.GET.get("form") or "").strip()
        focused_form = self._resolve_focus(focused_forms, focus_form_id)

        context["back_url"] = reverse(
            "subject:subject_list", kwargs={"study_id": self.get_study_id()},
        )
        context["subject_obj"] = subject
        context["subject_display_id"] = subject.subject_code or subject.screening_code or "—"
        context["event_navigation"] = event_navigation
        context["focused_event"] = focused_event
        context["focused_forms"] = focused_forms
        context["focused_form"] = focused_form
        context["study_header_label"] = subject.study.name or subject.study.code
        return context


class SubjectCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SubjectAbstractVerifyStudy,
):
    permission_required = "subject.create_subject"
    raise_exception = True

    def post(self, request, *args, **kwargs):
        study_id = self.get_study_id()
        site_id = SiteDropdownHandler(
            request=request,
            study_id=study_id,
        ).build().selected_id
        if site_id is None:
            raise Http404

        subject = CreateSubjectService().execute(
            CreateSubjectCommand(
                study_id=study_id,
                site_id=site_id,
                actor_user_id=request.user.pk,
            ),
        )
        return redirect(
            reverse(
                "subject:subject_detail",
                kwargs={"study_id": study_id, "subject_id": subject.pk},
            ),
        )
