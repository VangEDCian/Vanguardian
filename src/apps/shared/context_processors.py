from django.utils.translation import gettext_lazy as _


def _build_study_select_options():
    try:
        from apps.study.infrastructure.persistence.models import Study
        studies = Study.objects.filter(is_active=True, deleted=False).order_by("code").values("id", "code", "name")
        return [{"value": str(s["id"]), "label": f"{s['code']} — {s['name']}"} for s in studies]
    except Exception:
        return []


def shared_select_options(request):
    study_options = _build_study_select_options()
    study_default = study_options[0]["label"] if study_options else _("Select study")

    return {
        "shared_study_select_default": study_default,
        "shared_study_select_options": study_options,
        "shared_site_select_default": "100-JHU1",
        "shared_site_select_options": [
            {"value": "100-JHU1", "label": "100-JHU1"},
            {"value": "100-JHU2", "label": "100-JHU2"},
            {"value": "200-MAYO", "label": "200-MAYO"},
            {"value": "300-UCLA", "label": "300-UCLA"},
        ],
        "shared_language_select_options": [
            {"value": "vi", "label": _("Vietnamese")},
            {"value": "en", "label": _("English")},
        ],
    }
