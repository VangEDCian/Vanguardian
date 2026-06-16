from django.utils.translation import gettext_lazy as _

from apps.study.application.use_cases.randomization_import_preview.base import BaseRandomizationImportPreviewUseCase
from apps.study.application.use_cases.randomization_import_preview.types import RandomizationImportColumn


class RandomizationArmImportPreviewUseCase(BaseRandomizationImportPreviewUseCase):
    columns = (
        RandomizationImportColumn(
            "scheme_code",
            "Scheme Code",
            max_length=64,
            aliases=("Scheme",),
        ),
        RandomizationImportColumn(
            "arm_code",
            "Code",
            max_length=32,
            aliases=("Arm Code",),
        ),
        RandomizationImportColumn(
            "arm_name",
            "Name",
            max_length=255,
            aliases=("Arm Name",),
        ),
        RandomizationImportColumn(
            "target_count",
            "Target Count",
            data_type="integer",
        ),
        RandomizationImportColumn(
            "display_order",
            "Display Order",
            data_type="integer",
            aliases=("Order",),
        ),
        RandomizationImportColumn(
            "is_active",
            "Is Active",
            data_type="boolean",
            required=False,
            aliases=("Active",),
        ),
        RandomizationImportColumn(
            "notes",
            "Notes",
            required=False,
        ),
    )

    def _build_identifier(self, cleaned_values, row_data):
        scheme_code = cleaned_values.get("scheme_code") or self._as_text(row_data.get("scheme_code"))
        arm_code = cleaned_values.get("arm_code") or self._as_text(row_data.get("arm_code"))
        return " / ".join(part for part in (str(scheme_code).strip(), str(arm_code).strip()) if part)

    def _build_identifier_from_row_data(self, row_data):
        return " / ".join(
            part
            for part in (
                self._as_text(row_data.get("scheme_code")),
                self._as_text(row_data.get("arm_code")),
            )
            if part
        ) or str(_("(no code)"))

    def _build_duplicate_key(self, cleaned_values):
        return (
            str(cleaned_values.get("scheme_code", "")).lower(),
            str(cleaned_values.get("arm_code", "")).lower(),
        )

    def _get_duplicate_column_label(self):
        return "Scheme Code / Code"
