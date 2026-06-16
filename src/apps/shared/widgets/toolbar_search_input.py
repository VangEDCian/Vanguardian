from django import forms
from django.utils.translation import gettext_lazy as _


class ToolbarSearchInputWidget(forms.TextInput):
    template_name = "shared/widgets/toolbar_search_input.html"

    def __init__(
        self,
        *args,
        aria_label=None,
        show_icon=True,
        **kwargs,
    ):
        self.aria_label = aria_label if aria_label is not None else _("Search records")
        self.show_icon = show_icon
        super().__init__(*args, **kwargs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["show_icon"] = self.show_icon
        context["widget"]["attrs"]["aria-label"] = context["widget"]["attrs"].get(
            "aria-label",
            self.aria_label,
        )
        return context
