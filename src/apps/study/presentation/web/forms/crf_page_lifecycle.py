from django import forms
from django.utils.translation import gettext_lazy as _

from apps.study.application.services.crf_page_lifecycle import CrfPageLifecycleStep

STEP_LABELS = {
    CrfPageLifecycleStep.VERIFY: _("Verify Page"),
    CrfPageLifecycleStep.FINALIZE: _("Finalize Page Data"),
    CrfPageLifecycleStep.LOCK: _("Lock Page"),
}


class StudyCrfPageLifecycleForm(forms.Form):
    def __init__(self, *args, configuration: dict, **kwargs):
        super().__init__(*args, **kwargs)
        role_choices = [
            (str(role["id"]), f"{role['name']} ({role['scope_level']})")
            for role in configuration["roles"]
        ]
        configured_by_code = {step["code"]: step for step in configuration["steps"]}
        for step_code in CrfPageLifecycleStep.ALL:
            step = configured_by_code[step_code]
            self.fields[f"enabled_{step_code}"] = forms.BooleanField(required=False)
            self.fields[f"order_{step_code}"] = forms.IntegerField(
                min_value=1,
                max_value=len(CrfPageLifecycleStep.ALL),
                required=False,
            )
            self.fields[f"roles_{step_code}"] = forms.MultipleChoiceField(
                choices=role_choices,
                required=False,
            )
            if not self.is_bound:
                self.initial[f"enabled_{step_code}"] = step["enabled"]
                self.initial[f"order_{step_code}"] = step["display_order"]
                self.initial[f"roles_{step_code}"] = [
                    str(role_id) for role_id in step["allowed_role_ids"]
                ]
        self.configuration = configuration

    def clean(self):
        cleaned = super().clean()
        enabled_orders = []
        for step_code in CrfPageLifecycleStep.ALL:
            if not cleaned.get(f"enabled_{step_code}"):
                continue
            order = cleaned.get(f"order_{step_code}")
            roles = cleaned.get(f"roles_{step_code}") or []
            if order is None:
                self.add_error(f"order_{step_code}", _("Order is required for enabled steps."))
            else:
                enabled_orders.append(order)
            if not roles:
                self.add_error(f"roles_{step_code}", _("Select at least one role."))
        if enabled_orders and len(enabled_orders) != len(set(enabled_orders)):
            self.add_error(None, _("Enabled steps must have unique order numbers."))
        return cleaned

    def rows(self) -> list[dict]:
        return [
            {
                "code": step_code,
                "label": STEP_LABELS[step_code],
                "permission": CrfPageLifecycleStep.PERMISSION_BY_STEP[step_code],
                "enabled_field": self[f"enabled_{step_code}"],
                "order_field": self[f"order_{step_code}"],
                "roles_field": self[f"roles_{step_code}"],
            }
            for step_code in CrfPageLifecycleStep.ALL
        ]

    def raw_steps(self) -> list[dict]:
        return [
            {
                "step_code": step_code,
                "enabled": bool(self.cleaned_data.get(f"enabled_{step_code}")),
                "display_order": self.cleaned_data.get(f"order_{step_code}"),
                "role_ids": self.cleaned_data.get(f"roles_{step_code}") or (),
            }
            for step_code in CrfPageLifecycleStep.ALL
        ]


__all__ = ["StudyCrfPageLifecycleForm"]
