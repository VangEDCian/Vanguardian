from django import forms
from django.utils.translation import gettext_lazy as _


class ToolbarFilterSelectWidget(forms.Select):
    template_name = "shared/widgets/toolbar_filter_select.html"

    def __init__(
        self,
        *args,
        filter_label=None,
        aria_label=None,
        select_wrapper_class="common-select--filter",
        **kwargs,
    ):
        self.filter_label = filter_label if filter_label is not None else _("Filter:")
        self.aria_label = aria_label if aria_label is not None else _("Filter records")
        self.select_wrapper_class = select_wrapper_class
        super().__init__(*args, **kwargs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        normalized_value = "" if value in (None, "") else str(value)
        filter_options = [
            {
                "value": str(option_value),
                "label": option_label,
                "selected": str(option_value) == normalized_value,
            }
            for option_value, option_label in self.choices
        ]
        selected_display_text = next(
            (option["label"] for option in filter_options if option["selected"]),
            filter_options[0]["label"] if filter_options else self.filter_label,
        )
        for option in filter_options:
            if option["selected"]:
                selected_display_text = option["label"]
                break
        context["widget"]["filter_label"] = self.filter_label
        context["widget"]["select_wrapper_class"] = self.select_wrapper_class
        context["widget"]["select_aria_label"] = self.aria_label
        context["widget"]["filter_options"] = filter_options
        context["widget"]["select_value"] = normalized_value
        context["widget"]["select_display_text"] = selected_display_text
        return context
