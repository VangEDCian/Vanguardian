from django import forms
from django.utils.translation import gettext_lazy as _


class EventFormDisplayLabelConfigForm(forms.Form):
    EMPTY_VALUE_POLICY_CHOICES = (
        ("FALLBACK", _("Fallback")),
        ("EMPTY_TEXT", _("Empty Text")),
        ("OMIT_TOKEN", _("Omit Token")),
    )

    event_form_binding_id = forms.ChoiceField(
        label=_("Event Form Binding"),
        choices=(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    is_enabled = forms.BooleanField(
        label=_("Enable instance display label"),
        required=False,
    )
    max_length = forms.IntegerField(
        label=_("Max Length"),
        min_value=20,
        max_value=255,
        initial=120,
    )
    use_choice_display_label = forms.BooleanField(
        label=_("Use translated choice label"),
        required=False,
        initial=True,
    )
    empty_value_policy = forms.ChoiceField(
        label=_("Empty Value Policy"),
        choices=EMPTY_VALUE_POLICY_CHOICES,
        initial="FALLBACK",
    )
    label_template_vi = forms.CharField(
        label=_("Vietnamese Label Template"),
        widget=forms.Textarea(attrs={"rows": 3, "id": "id_label_template_vi"}),
    )
    fallback_template_vi = forms.CharField(
        label=_("Vietnamese Fallback Template"),
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    empty_value_text_vi = forms.CharField(
        label=_("Vietnamese Empty Text"),
        required=False,
    )
    label_template_en = forms.CharField(
        label=_("English Label Template"),
        widget=forms.Textarea(attrs={"rows": 3, "id": "id_label_template_en"}),
    )
    fallback_template_en = forms.CharField(
        label=_("English Fallback Template"),
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    empty_value_text_en = forms.CharField(
        label=_("English Empty Text"),
        required=False,
    )
    sample_repeat_index = forms.IntegerField(
        label=_("Sample Repeat Index"),
        min_value=1,
        initial=1,
    )
    sample_field_values = forms.JSONField(
        label=_("Sample Field Values"),
        required=False,
        initial=dict,
        help_text=_("Provide a JSON object keyed by field key for preview."),
        widget=forms.Textarea(attrs={"rows": 8}),
    )

    def __init__(self, *args, binding_choices=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["event_form_binding_id"].choices = binding_choices
        self.fields["sample_field_values"].initial = self.initial.get("sample_field_values") or {}


__all__ = ["EventFormDisplayLabelConfigForm"]
