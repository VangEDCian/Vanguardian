from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import JsonResponse
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View

from apps.crf.application.form_builder_queries import FormBuilderReadModelService
from apps.crf.presentation.web.views.builder_support import CrfFormBuilderSupportMixin


class CrfFormBuilderTreeApiView(
    CrfFormBuilderSupportMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin,
    View,
):
    permission_required = "study.view_study_detail"
    raise_exception = True
    read_model_service_class = FormBuilderReadModelService

    def get(self, request, *args, **kwargs):
        builder = self.get_builder()
        self.ensure_study_scope(builder)

        node_id = (request.GET.get("node_id") or "#").strip()
        selected_section_id = self.get_selected_section_id()
        selected_field_id = self.get_selected_field_id()

        nodes = self._build_nodes(
            builder=builder,
            node_id=node_id,
            selected_section_id=selected_section_id,
            selected_field_id=selected_field_id,
        )
        return JsonResponse({"nodes": nodes})

    def _build_nodes(self, *, builder, node_id, selected_section_id, selected_field_id):
        template = builder.get("template", {}) or {}
        form_id = int(template.get("id") or self.kwargs["form_id"])
        form_key = f"form-{form_id}"

        if node_id == "#":
            return [
                {
                    "id": form_key,
                    "text": f"[FORM] {template.get('code') or 'FORM'}",
                    "children": True,
                    "state": {"opened": True},
                }
            ]

        if node_id == form_key:
            sections = builder.get("sections", []) or []
            if not sections:
                return [
                    {
                        "id": f"{form_key}-no-sections",
                        "text": _("No sections"),
                        "children": False,
                        "state": {"disabled": True},
                    }
                ]

            return [
                self._serialize_section_node(
                    form_id=form_id,
                    section=section,
                    index=index,
                    selected_section_id=selected_section_id,
                    selected_field_id=selected_field_id,
                )
                for index, section in enumerate(sections, start=1)
            ]

        if node_id.startswith("section-"):
            return []

        return []

    def _serialize_section_node(self, *, form_id, section, index, selected_section_id, selected_field_id):
        section_id = section.get("id")
        section_key = f"section-{section_id}" if section_id is not None else f"section-unassigned-{index}"
        section_code = section.get("section_code") or section.get("section_name") or "SECTION"

        href = reverse("crf:form_builder", kwargs={"form_id": form_id})
        if section_id is not None:
            href = f"{href}?section_id={section_id}"

        section_selected = section_id is not None and selected_section_id is not None and int(section_id) == int(selected_section_id)
        contains_selected_field = False
        if selected_field_id is not None:
            for field in section.get("fields", []) or []:
                try:
                    if int(field.get("id")) == int(selected_field_id):
                        contains_selected_field = True
                        break
                except (TypeError, ValueError):
                    continue

        return {
            "id": section_key,
            "text": f"[SEC] {section_code}",
            "children": False,
            "state": {
                "opened": False,
                "selected": bool(section_selected or contains_selected_field),
            },
            "li_attr": {
                "data-href": href,
            },
        }
