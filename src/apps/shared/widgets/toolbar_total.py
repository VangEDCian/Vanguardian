from django import forms
from django.utils.translation import gettext_lazy as _


class ToolbarTotalWidget(forms.Widget):
    template_name = "shared/widgets/toolbar_total.html"

    def __init__(self, *args, total_label=None, total_value=0, **kwargs):
        self.total_label = total_label if total_label is not None else _("Total")
        self.total_value = total_value
        super().__init__(*args, **kwargs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["total_label"] = self.total_label
        context["widget"]["total_value"] = self.total_value
        return context
