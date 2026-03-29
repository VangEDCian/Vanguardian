from django.utils.translation import gettext_lazy as _


def shared_select_options(request):
    return {
        "shared_study_select_default": _("REACT-AF Training"),
        "shared_study_select_options": [
            {"value": "react-af-training", "label": _("REACT-AF Training")},
            {"value": "react-af-phase-ii", "label": _("REACT-AF Phase II")},
            {"value": "cardio-study-1", "label": _("CARDIO-Study 1")},
        ],
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
