from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from django_filters.views import FilterView
from django_tables2 import SingleTableMixin

from apps.crf.public import get_crf_template_model
from apps.shared.views import AuthenticateTemplateContextMixin
from apps.study.application import (
    CrfTemplateImportDependencyError,
    CrfTemplateImportFormatError,
    ImportStudyCrfTemplateFieldsTemplateResult,
    ImportStudyCrfTemplateFieldsTemplateService,
    ImportStudyCrfTemplatesTemplateService,
    StudyDirectoryQueryService,
    StudyNotFoundError,
)
from apps.study.application.commands.import_crf_template_fields_template import (
    CrfTemplateFieldImportIssue,
)
from apps.study.infrastructure.persistence.models import Study
from apps.study.presentation.web.forms import (
    CrfTemplateFieldsImportTemplateForm,
    CrfTemplateImportTemplateForm,
    CrfTemplatesToolbarForm,
)
from apps.study.presentation.web.mappers.commands import (
    to_import_study_crf_template_fields_template_command,
    to_import_study_crf_templates_template_command,
)
from apps.study.presentation.web.tables import CrfTemplateListTable
from apps.study.presentation.web.views.helpers import _user_has_study_access


class StudyCrfTemplateListView(
    AuthenticateTemplateContextMixin,
    SingleTableMixin, FilterView, ListView,
):
    permission_required = "study.view_study_detail"
    raise_exception = True
    template_name = "study/crf_templates.html"
    layout_nav_key = "STUDIES"
    model = get_crf_template_model()
    table_class = CrfTemplateListTable
    filterset_class = CrfTemplatesToolbarForm
    context_table_name = "crf_templates_table"
    paginate_by = 25

    study_directory_query_service_class = StudyDirectoryQueryService
    import_crf_templates_template_service_class = ImportStudyCrfTemplatesTemplateService
    import_crf_template_fields_template_service_class = ImportStudyCrfTemplateFieldsTemplateService
    expected_import_columns = ImportStudyCrfTemplatesTemplateService.expected_columns
    expected_field_import_columns = ImportStudyCrfTemplateFieldsTemplateService.expected_columns
    _detail_view_model = None
    _study = None

    def get_study_directory_query_service(self):
        return self.study_directory_query_service_class()

    def get_import_crf_templates_template_service(self):
        return self.import_crf_templates_template_service_class()

    def get_import_crf_template_fields_template_service(self):
        return self.import_crf_template_fields_template_service_class()

    def dispatch(self, request, *args, **kwargs):
        self._study = Study.objects.filter(pk=kwargs["study_id"], deleted=False).first()
        if self._study is None:
            raise Http404

        try:
            self._detail_view_model = (
                self.get_study_directory_query_service().get_study_detail(
                    study_id=kwargs["study_id"]
                )
            )
        except StudyNotFoundError as exc:
            raise Http404 from exc

        if not _user_has_study_access(request.user, kwargs["study_id"]):
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)

    def get_layout_breadcrumb_label(self):
        if self._detail_view_model is None:
            return super().get_layout_breadcrumb_label()
        return self._detail_view_model["layout_breadcrumb_label"]

    def get_layout_show_breadcrumb_trail(self):
        return False

    def get_layout_detail_meta_items(self):
        if self._detail_view_model is None:
            return super().get_layout_detail_meta_items()
        return self._detail_view_model.get("layout_detail_meta_items", ())

    def get_queryset(self):
        return super().get_queryset().filter(
            study_id=self._study.pk,
            deleted=False,
        ).prefetch_related("translations")

    def get_table(self, **kwargs):
        table = super().get_table(**kwargs)
        table.empty_text = _("No CRF templates found matching your criteria.")
        return table

    @staticmethod
    def _build_hidden_fields(**params):
        return [{"name": name, "value": value} for name, value in params.items() if value not in (None, "")]

    def _build_table_toolbar(self, *, total, search_query, sort_query):
        return {
            "filter": None,
            "secondary_search": None,
            "summary": {
                "label": _("Total CRF Templates"),
                "value": total,
            },
            "search": {
                "name": "search",
                "value": search_query,
                "placeholder": _("Search CRF templates..."),
                "aria_label": _("Search CRF templates"),
                "show_icon": True,
                "hidden_fields": self._build_hidden_fields(sort=sort_query),
            },
        }

    def _ensure_filter_state(self):
        if not hasattr(self, "filterset"):
            self.filterset = self.get_filterset(self.get_filterset_class())
        if not hasattr(self, "object_list"):
            self.object_list = self.filterset.qs

    def get_context_data(self, **kwargs):
        self._ensure_filter_state()
        context = super().get_context_data(**kwargs)
        context["detail_study"] = self._detail_view_model["detail_study"]
        search_query = (self.request.GET.get("search", "") or "").strip()
        sort_query = self.request.GET.get("sort", "")
        context["crf_templates_total"] = self.filterset.qs.count()
        context["crf_templates_empty_text"] = _("No CRF templates found matching your criteria.")
        context["crf_templates_table_toolbar"] = self._build_table_toolbar(
            total=context["crf_templates_total"],
            search_query=search_query,
            sort_query=sort_query,
        )
        context["crf_template_search_query"] = search_query
        context.setdefault("import_form", CrfTemplateImportTemplateForm())
        context.setdefault("field_import_form", CrfTemplateFieldsImportTemplateForm())
        context["expected_import_columns"] = self.expected_import_columns
        context["expected_field_import_columns"] = self.expected_field_import_columns
        context["import_result"] = kwargs.get("import_result")
        context["field_import_result"] = kwargs.get("field_import_result")
        context["import_modal_open"] = kwargs.get(
            "import_modal_open",
            self.request.GET.get("open_import_modal") == "1",
        )
        context["field_import_modal_open"] = kwargs.get(
            "field_import_modal_open",
            self.request.GET.get("open_field_import_modal") == "1",
        )
        return context

    def post(self, request, *args, **kwargs):
        import_form = CrfTemplateImportTemplateForm(request.POST, request.FILES)
        if not import_form.is_valid():
            return self.render_to_response(
                self.get_context_data(import_form=import_form, import_modal_open=True)
            )

        uploaded_file = import_form.cleaned_data["import_file"]
        command = to_import_study_crf_templates_template_command(
            actor_user_id=request.user.pk,
            selected_study_id=self._study.pk,
            study_id=self._study.pk,
            file_name=uploaded_file.name,
            file_content=uploaded_file.read(),
        )
        try:
            import_result = self.get_import_crf_templates_template_service().execute(command)
        except (CrfTemplateImportDependencyError, CrfTemplateImportFormatError) as exc:
            import_form.add_error(None, str(exc))
            return self.render_to_response(
                self.get_context_data(import_form=import_form, import_modal_open=True)
            )

        if import_result.skipped_count == 0 and not import_result.warnings:
            return redirect(
                reverse("study:study_crf_templates", kwargs={"study_id": self._study.pk})
            )

        return self.render_to_response(
            self.get_context_data(
                import_form=CrfTemplateImportTemplateForm(),
                import_result=import_result,
                import_modal_open=True,
            )
        )


class StudyCrfTemplateImportTemplateView(StudyCrfTemplateListView):
    raise_exception = True

    def get(self, request, *args, **kwargs):
        return redirect(
            reverse("study:study_crf_templates", kwargs={"study_id": self._study.pk}) + "?open_import_modal=1"
        )


class StudyCrfTemplateFieldImportTemplateView(StudyCrfTemplateListView):
    raise_exception = True

    def get(self, request, *args, **kwargs):
        return redirect(
            reverse("study:study_crf_templates", kwargs={"study_id": self._study.pk}) + "?open_field_import_modal=1"
        )

    @staticmethod
    def _add_file_context_to_issues(*, file_name, issues):
        return tuple(
            CrfTemplateFieldImportIssue(
                sheet_name=f"{file_name} / {issue.sheet_name}",
                row_number=issue.row_number,
                identifier=issue.identifier,
                reason=issue.reason,
            )
            for issue in issues
        )

    def _import_field_template_files(self, *, uploaded_files, actor_user_id):
        service = self.get_import_crf_template_fields_template_service()
        total_rows = 0
        created_count = 0
        updated_count = 0
        skipped_count = 0
        issues = []
        warnings = []

        for uploaded_file in uploaded_files:
            command = to_import_study_crf_template_fields_template_command(
                actor_user_id=actor_user_id,
                selected_study_id=self._study.pk,
                study_id=self._study.pk,
                file_name=uploaded_file.name,
                file_content=uploaded_file.read(),
            )
            try:
                file_result = service.execute(command)
            except (CrfTemplateImportDependencyError, CrfTemplateImportFormatError) as exc:
                skipped_count += 1
                issues.append(
                    CrfTemplateFieldImportIssue(
                        sheet_name=uploaded_file.name,
                        row_number=0,
                        identifier=uploaded_file.name,
                        reason=str(exc),
                    )
                )
                continue

            total_rows += file_result.total_rows
            created_count += file_result.created_count
            updated_count += file_result.updated_count
            skipped_count += file_result.skipped_count
            issues.extend(
                self._add_file_context_to_issues(
                    file_name=uploaded_file.name,
                    issues=file_result.issues,
                )
            )
            warnings.extend(file_result.warnings)

        return ImportStudyCrfTemplateFieldsTemplateResult(
            total_rows=total_rows,
            created_count=created_count,
            updated_count=updated_count,
            skipped_count=skipped_count,
            issues=tuple(issues),
            warnings=tuple(warnings),
        )

    def post(self, request, *args, **kwargs):
        import_form = CrfTemplateFieldsImportTemplateForm(request.POST, request.FILES)
        if not import_form.is_valid():
            return self.render_to_response(
                self.get_context_data(field_import_form=import_form, field_import_modal_open=True)
            )

        import_result = self._import_field_template_files(
            uploaded_files=import_form.cleaned_data["import_file"],
            actor_user_id=request.user.pk,
        )

        if import_result.skipped_count == 0 and not import_result.warnings:
            return redirect(
                reverse("study:study_crf_templates", kwargs={"study_id": self._study.pk})
            )

        return self.render_to_response(
            self.get_context_data(
                field_import_form=CrfTemplateFieldsImportTemplateForm(),
                field_import_result=import_result,
                field_import_modal_open=True,
            )
        )
