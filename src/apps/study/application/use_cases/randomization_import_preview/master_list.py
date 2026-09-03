from django.utils.translation import gettext_lazy as _

from apps.study.application.use_cases.randomization_import_preview.base import (
    BaseRandomizationImportPreviewUseCase,
)
from apps.study.application.use_cases.randomization_import_preview.types import (
    RandomizationImportColumn,
    RandomizationImportFormatError,
)


class Nng31RandomizationMasterListImportPreviewUseCase(
    BaseRandomizationImportPreviewUseCase
):
    columns = (
        RandomizationImportColumn("scheme_code", "Scheme Code", max_length=64),
        RandomizationImportColumn(
            "randomization_code",
            "Randomization ID",
            max_length=64,
        ),
        RandomizationImportColumn("sequence_no", "Sequence No", data_type="integer"),
        RandomizationImportColumn("block_no", "Block No", data_type="integer"),
        RandomizationImportColumn("arm_code", "Arm Code", max_length=32),
    )

    def _coerce_int(self, value, *, field_label):
        parsed_value = super()._coerce_int(value, field_label=field_label)
        if parsed_value <= 0:
            raise RandomizationImportFormatError(
                str(_("%(column)s must be greater than zero.") % {"column": field_label})
            )
        return parsed_value

    def _build_identifier(self, cleaned_values, row_data):
        return str(
            cleaned_values.get("randomization_code")
            or row_data.get("randomization_code")
            or _("(no randomization ID)")
        ).strip()

    def _build_identifier_from_row_data(self, row_data):
        return str(
            row_data.get("randomization_code") or _("(no randomization ID)")
        ).strip()

    def _build_duplicate_key(self, cleaned_values):
        return (
            str(cleaned_values.get("scheme_code", "")).strip().lower(),
            str(cleaned_values.get("randomization_code", "")).strip().lower(),
        )

    def _get_duplicate_column_label(self):
        return "Scheme Code / Randomization ID"


__all__ = ["Nng31RandomizationMasterListImportPreviewUseCase"]
