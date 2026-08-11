from django.db.models import Q

from apps.datacapture.models import DataCapturePageState


class DjangoSubjectExportDataRepository:
    def list_page_state_rows(
        self,
        *,
        study_id: int,
        site_id: int,
        subject_ids: tuple[int, ...],
        field_specs: tuple[dict, ...],
    ):
        binding_ids = tuple(
            dict.fromkeys(int(spec["binding_id"]) for spec in field_specs)
        )
        event_definition_ids = tuple(
            dict.fromkeys(
                int(spec["event_definition_id"])
                for spec in field_specs
            )
        )
        crf_template_ids = tuple(
            dict.fromkeys(int(spec["crf_template_id"]) for spec in field_specs)
        )
        selected_scope = Q(event_form_binding_id__in=binding_ids) | Q(
            visit__event_definition_id__in=event_definition_ids,
            crf_template_id__in=crf_template_ids,
        )
        return tuple(
            DataCapturePageState.objects.filter(
                selected_scope,
                subject_id__in=subject_ids,
                subject__study_id=study_id,
                subject__site_id=site_id,
                subject__deleted=False,
                deleted=False,
            )
            .values(
                "id",
                "subject_id",
                "event_form_binding_id",
                "crf_template_id",
                "visit_id",
                "visit__event_definition_id",
                "visit__event_definition__sequence_no",
                "visit__repeat_index",
                "repeat_index",
                "final_data",
                "current_entry__data",
            )
            .order_by(
                "subject_id",
                "visit__event_definition__sequence_no",
                "visit__repeat_index",
                "visit_id",
                "repeat_index",
                "id",
            )
        )


__all__ = ["DjangoSubjectExportDataRepository"]
