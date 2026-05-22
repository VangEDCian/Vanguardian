import json

from django import forms


class CrfFieldCreateForm(forms.Form):
    CONTROL_TYPE_BY_DATA_TYPE = {
        "BOOLEAN": "checkbox_list",
        "CODELIST": "dropdown",
        "DATE": "date_picker",
        "DATETIME": "date_picker",
        "DECIMAL": "entry_box",
        "INTEGER": "entry_box",
        "NUMBER": "entry_box",
        "STRING": "dropdown",
        "TEXT": "entry_box",
        "TEXTAREA": "text_area",
        "TIME": "time_picker",
    }

    DATA_TYPE_CHOICES = [
        ("BOOLEAN", "Boolean"),
        ("CODELIST", "Codelist"),
        ("DATE", "Date"),
        ("DATETIME", "DateTime"),
        ("DECIMAL", "Decimal"),
        ("INTEGER", "Integer"),
        ("NUMBER", "Number"),
        ("STRING", "String"),
        ("TEXT", "Text"),
        ("TEXTAREA", "Text Area"),
        ("TIME", "Time"),
    ]

    CONTROL_TYPE_CHOICES = [
        ("checkbox_list", "Checkbox List"),
        ("dropdown", "Dropdown"),
        ("select2", "Select2"),
        ("date_picker", "Date Picker"),
        ("date_text", "Date Text"),
        ("entry_box", "Entry Box"),
        ("text_area", "Text Area"),
        ("time_picker", "Time Picker"),
        ("datetime_text", "DateTime Text"),
    ]

    field_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    field_key = forms.CharField(max_length=100)
    data_type = forms.ChoiceField(choices=DATA_TYPE_CHOICES)
    is_active = forms.BooleanField(required=False, initial=True)
    display_order = forms.IntegerField(required=False, initial=1, min_value=1)
    section_template_id = forms.ChoiceField(required=False, choices=())
    label_en = forms.CharField(required=False, max_length=255)
    label_vi = forms.CharField(required=False, max_length=255)

    sdtm = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}))
    unit = forms.CharField(required=False)
    range_min = forms.DecimalField(required=False, max_digits=21, decimal_places=6)
    range_max = forms.DecimalField(required=False, max_digits=21, decimal_places=6)
    precision = forms.IntegerField(required=False, min_value=0)
    allowed_missing_values = forms.CharField(required=False)
    codelist = forms.CharField(required=False)
    data_semantic = forms.CharField(required=False)
    comments = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    text_max_length = forms.IntegerField(required=False, min_value=1)
    text_min_length = forms.IntegerField(required=False, min_value=0)
    pattern = forms.CharField(required=False)
    pattern_err_msg = forms.CharField(required=False)

    control_type = forms.ChoiceField(required=False, choices=CONTROL_TYPE_CHOICES)
    layout = forms.CharField(required=False)
    text = forms.CharField(required=False)
    behavior = forms.CharField(required=False)
    options = forms.CharField(required=False)
    style = forms.CharField(required=False)

    validation_rules_json = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 5}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_shared_input_styles()

    def set_section_template_choices(self, choices):
        self.fields["section_template_id"].choices = [("", "Select section")] + list(choices)
        self._mark_select2_field("section_template_id")

    def clean(self):
        cleaned_data = super().clean()
        field_id = cleaned_data.get("field_id")
        section_template_id = cleaned_data.get("section_template_id")

        if not field_id and section_template_id is None:
            self.add_error("section_template_id", "Please select a section before creating a field.")

        return cleaned_data

    def _mark_select2_field(self, field_name):
        widget = self.fields[field_name].widget
        select_classes = [name for name in widget.attrs.get("class", "").split() if name]
        if "old-select2-single-choice" not in select_classes:
            select_classes.append("old-select2-single-choice")
        widget.attrs["class"] = " ".join(select_classes)

    def _apply_shared_input_styles(self):
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.HiddenInput) or isinstance(widget, forms.CheckboxInput):
                continue

            if isinstance(widget, forms.Select):
                self._mark_select2_field(field_name)
                continue

            attrs = widget.attrs
            existing_class = attrs.get("class", "")
            class_names = [name for name in existing_class.split() if name]
            if "old-textbox" not in class_names:
                class_names.append("old-textbox")
            attrs["class"] = " ".join(class_names)

            if isinstance(widget, forms.Textarea) and "rows" not in attrs:
                attrs["rows"] = 3

            if field_name == "sdtm":
                attrs.setdefault("placeholder", "domain + variable + role")
            elif field_name == "validation_rules_json":
                attrs.setdefault("placeholder", "[]")
            elif field_name in {
                "description_en",
                "description_vi",
                "help_text_en",
                "help_text_vi",
                "instruction_text_en",
                "instruction_text_vi",
                "comments",
                "pattern_err_msg",
            }:
                attrs.setdefault("placeholder", "")

    def clean_section_template_id(self):
        raw_value = self.cleaned_data.get("section_template_id")
        if raw_value in (None, ""):
            return None
        return int(raw_value)

    def clean_data_type(self):
        raw_value = self.cleaned_data.get("data_type")
        return (raw_value or "").strip().upper()

    def clean_validation_rules_json(self):
        raw_value = (self.cleaned_data.get("validation_rules_json") or "").strip()
        if not raw_value:
            return []
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError("validation_rules_json must be valid JSON.") from exc
        if not isinstance(parsed, list):
            raise forms.ValidationError("validation_rules_json must be a JSON list.")
        return parsed

    def _get_choice_label(self, field_name, value):
        choices = dict(self.fields[field_name].choices)
        normalized_value = value if value not in (None, "") else ""
        return choices.get(normalized_value, normalized_value or "")

    def get_control_type_label(self):
        cleaned_data = getattr(self, "cleaned_data", None) or {}
        return self._get_choice_label("control_type", cleaned_data.get("control_type") or self.initial.get("control_type"))

    def get_data_type_label(self):
        cleaned_data = getattr(self, "cleaned_data", None) or {}
        return self._get_choice_label("data_type", cleaned_data.get("data_type") or self.initial.get("data_type"))

    def get_definition_payload(self):
        return {
            "sdtm": self.cleaned_data.get("sdtm", "") or "",
            "unit": self.cleaned_data.get("unit"),
            "range_min": self.cleaned_data.get("range_min"),
            "range_max": self.cleaned_data.get("range_max"),
            "precision": self.cleaned_data.get("precision"),
            "allowed_missing_values": self.cleaned_data.get("allowed_missing_values", "") or "",
            "codelist": self.cleaned_data.get("codelist"),
            "data_semantic": self.cleaned_data.get("data_semantic"),
            "comments": self.cleaned_data.get("comments"),
            "text_max_length": self.cleaned_data.get("text_max_length"),
            "text_min_length": self.cleaned_data.get("text_min_length"),
            "pattern": self.cleaned_data.get("pattern"),
            "pattern_err_msg": self.cleaned_data.get("pattern_err_msg"),
        }

    def get_ui_config_payload(self):
        data_type = self.cleaned_data.get("data_type", "") or ""
        control_type = (self.cleaned_data.get("control_type") or "").strip()
        expected_control_type = self.CONTROL_TYPE_BY_DATA_TYPE.get(data_type)

        if control_type == "select2":
            control_type = "select2"
        elif data_type == "DATE" and control_type == "date_text":
            control_type = "date_text"
        elif data_type == "DATETIME" and control_type == "datetime_text":
            control_type = "datetime_text"
        elif expected_control_type:
            control_type = expected_control_type
        elif not control_type:
            control_type = "entry_box"
        return {
            "control_type": control_type,
            "layout": self.cleaned_data.get("layout"),
            "text": self.cleaned_data.get("text"),
            "behavior": self.cleaned_data.get("behavior"),
            "options": self.cleaned_data.get("options"),
            "style": self.cleaned_data.get("style"),
        }


class CrfFieldUpdateForm(CrfFieldCreateForm):
    rule_ids_json = forms.CharField(required=False, widget=forms.HiddenInput())


class CrfSectionTemplateForm(forms.Form):
    section_template_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    section_code = forms.CharField(max_length=64)
    section_name_en = forms.CharField(required=False, max_length=255)
    section_name_vi = forms.CharField(required=False, max_length=255)
    description_en = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    description_vi = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    help_text_en = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    help_text_vi = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    instruction_text_en = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    instruction_text_vi = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    display_order = forms.IntegerField(required=False, initial=1, min_value=1)
    is_required = forms.BooleanField(required=False, initial=True)
    is_repeatable = forms.BooleanField(required=False, initial=False)
    min_repeats = forms.IntegerField(required=False, initial=0, min_value=0)
    max_repeats = forms.IntegerField(required=False, min_value=1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_shared_input_styles()

    def _apply_shared_input_styles(self):
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.HiddenInput) or isinstance(widget, forms.CheckboxInput):
                continue

            attrs = widget.attrs
            existing_class = attrs.get("class", "")
            class_names = [name for name in existing_class.split() if name]
            if "old-textbox" not in class_names:
                class_names.append("old-textbox")
            attrs["class"] = " ".join(class_names)

            if isinstance(widget, forms.Textarea) and "rows" not in attrs:
                attrs["rows"] = 3

            if field_name == "section_code":
                attrs.setdefault("placeholder", "DEMO")


class CrfTemplateTranslationForm(forms.Form):
    template_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    code = forms.CharField(max_length=64, widget=forms.TextInput(attrs={"readonly": "readonly"}))
    version = forms.CharField(max_length=32, widget=forms.TextInput(attrs={"readonly": "readonly"}))
    name_en = forms.CharField(required=False, max_length=255)
    name_vi = forms.CharField(required=False, max_length=255)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.HiddenInput) or isinstance(widget, forms.CheckboxInput):
                continue
            class_names = [name for name in widget.attrs.get("class", "").split() if name]
            if "old-textbox" not in class_names:
                class_names.append("old-textbox")
            widget.attrs["class"] = " ".join(class_names)
