from django.utils.translation import gettext_lazy as _

from apps.crf.public import CrfContextAdapter


class StudyCrfTemplateDirectoryQueryService:
    crf_context_adapter_class = CrfContextAdapter

    def __init__(self, crf_context_adapter=None):
        self.crf_context_adapter = crf_context_adapter or self.crf_context_adapter_class()

    def list_crf_templates(self, *, study_id, search_query="", sort_query=""):
        normalized_search_query = (search_query or "").strip()

        crf_templates = list(
            self.crf_context_adapter.list_study_templates_for_listing(
                study_id=study_id,
            )
        )

        if normalized_search_query:
            search_term = normalized_search_query.casefold()
            crf_templates = [
                crf_template
                for crf_template in crf_templates
                if self._matches_search(crf_template, search_term)
            ]

        return {
            "crf_templates": crf_templates,
            "crf_templates_total": len(crf_templates),
            "crf_templates_empty_text": _("No CRF templates found matching your criteria."),
            "crf_templates_table_toolbar": self._build_table_toolbar(
                total=len(crf_templates),
                search_query=normalized_search_query,
                sort_query=sort_query,
            ),
            "crf_template_search_query": normalized_search_query,
        }

    def _matches_search(self, crf_template, search_term):
        return any(
            search_term in candidate
            for candidate in (
                self._normalize_text(crf_template.code),
                self._normalize_text(
                    crf_template.safe_translation_getter("name", default="", any_language=True)
                ),
                self._normalize_text(crf_template.version),
            )
        )

    def _build_table_toolbar(self, *, total, search_query, sort_query):
        return {
            "filter": None,
            "secondary_search": None,
            "summary": {
                "label": _("Total CRF Templates"),
                "value": total,
            },
            "search": {
                "name": "q",
                "value": search_query,
                "placeholder": _("Search CRF templates..."),
                "aria_label": _("Search CRF templates"),
                "show_icon": True,
                "hidden_fields": self._build_hidden_fields(sort=sort_query),
            },
        }

    @staticmethod
    def _normalize_text(value):
        return str(value or "").casefold()

    @staticmethod
    def _build_hidden_fields(**params):
        return [{"name": name, "value": value} for name, value in params.items() if value not in (None, "")]
