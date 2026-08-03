import re
from pathlib import Path

import django_filters
from django import forms
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.shared.filters import SharedSearch, SharedTotal
from apps.shared.widgets import ToolbarFilterSelectWidget
from apps.subject.application.services.eligibility_workflow import (
    SubjectEligibilityWorkflowService,
)
from apps.subject.models import Subject

MAX_EVENT_INSTANCE_IMPORT_FILE_SIZE_BYTES = 10 * 1024 * 1024
ALLOWED_EVENT_INSTANCE_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
ALLOWED_EVENT_INSTANCE_PDF_EXTENSIONS = {".pdf"}
ALLOWED_EVENT_INSTANCE_UPLOAD_EXTENSIONS = (
    ALLOWED_EVENT_INSTANCE_IMAGE_EXTENSIONS | ALLOWED_EVENT_INSTANCE_PDF_EXTENSIONS
)
ALLOWED_EVENT_INSTANCE_IMAGE_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/pjpeg",
    "image/gif",
    "image/bmp",
    "image/x-ms-bmp",
    "image/webp",
}
ALLOWED_EVENT_INSTANCE_PDF_MIME_TYPES = {"application/pdf"}
ALLOWED_EVENT_INSTANCE_UPLOAD_MIME_TYPES = (
    ALLOWED_EVENT_INSTANCE_IMAGE_MIME_TYPES | ALLOWED_EVENT_INSTANCE_PDF_MIME_TYPES
)

EARLY_TERMINATION_REASON_CHOICES = (
    ("adverse_event", _("Adverse event")),
    ("subject_withdrawal", _("Subject withdrawal")),
    ("investigator_decision", _("Investigator decision")),
    ("lost_to_follow_up", _("Lost to follow-up")),
    ("protocol_deviation", _("Protocol deviation")),
    ("other", _("Other")),
)
PERIOD_OVERRIDE_REASON_CHOICES = (
    ("paper_crf_delayed", _("Paper CRF delayed")),
    ("source_document_issue", _("Source document issue")),
    ("data_entry_backlog", _("Data entry backlog")),
    ("protocol_deviation", _("Protocol deviation")),
    ("other", _("Other")),
)

__all__ = [
    "ALLOWED_EVENT_INSTANCE_IMAGE_EXTENSIONS",
    "ALLOWED_EVENT_INSTANCE_IMAGE_MIME_TYPES",
    "ALLOWED_EVENT_INSTANCE_PDF_EXTENSIONS",
    "ALLOWED_EVENT_INSTANCE_PDF_MIME_TYPES",
    "ALLOWED_EVENT_INSTANCE_UPLOAD_EXTENSIONS",
    "ALLOWED_EVENT_INSTANCE_UPLOAD_MIME_TYPES",
    "MAX_EVENT_INSTANCE_IMPORT_FILE_SIZE_BYTES",
    "SubjectAuditHistoryFilterForm",
    "SubjectEventInstanceFileImportForm",
    "SubjectEarlyTerminationForm",
    "SubjectPeriodOverrideForm",
    "SubjectsToolbarForm",
    "detect_event_instance_upload_kind_from_header",
]


def detect_event_instance_upload_kind_from_header(file_header):
    if file_header.startswith(b"\xFF\xD8\xFF"):  # JPEG
        return "image"
    if file_header.startswith(b"\x89PNG\r\n\x1a\n"):  # PNG
        return "image"
    if file_header.startswith(b"GIF87a") or file_header.startswith(b"GIF89a"):  # GIF
        return "image"
    if file_header.startswith(b"BM"):  # BMP
        return "image"
    if file_header.startswith(b"RIFF") and file_header[8:12] == b"WEBP":  # WEBP
        return "image"
    if file_header.startswith(b"%PDF-"):  # PDF
        return "pdf"
    return None


def _validate_event_instance_upload_extension(uploaded_file):
    extension = Path(uploaded_file.name or "").suffix.lower().strip()
    if extension not in ALLOWED_EVENT_INSTANCE_UPLOAD_EXTENSIONS:
        raise forms.ValidationError(_("Unsupported file type. Only image and PDF are allowed."))
    return extension


def _validate_event_instance_upload_mime_type(uploaded_file):
    uploaded_mime_type = (getattr(uploaded_file, "content_type", "") or "").split(";", 1)[0].lower().strip()
    if uploaded_mime_type and uploaded_mime_type not in ALLOWED_EVENT_INSTANCE_UPLOAD_MIME_TYPES:
        raise forms.ValidationError(_("Unsupported file type. Only image and PDF are allowed."))
    return uploaded_mime_type


def _detect_event_instance_upload_kind(uploaded_file):
    file_header = uploaded_file.read(16)
    uploaded_file.seek(0)
    detected_kind = detect_event_instance_upload_kind_from_header(file_header)
    if detected_kind is None:
        raise forms.ValidationError(_("Invalid file content. Only valid image and PDF files are allowed."))
    return detected_kind


def _validate_event_instance_upload_kind_consistency(*, extension, uploaded_mime_type, detected_kind):
    extension_kind = "pdf" if extension in ALLOWED_EVENT_INSTANCE_PDF_EXTENSIONS else "image"
    if detected_kind != extension_kind:
        raise forms.ValidationError(_("File extension does not match file content."))

    if not uploaded_mime_type:
        return
    if detected_kind == "pdf" and uploaded_mime_type not in ALLOWED_EVENT_INSTANCE_PDF_MIME_TYPES:
        raise forms.ValidationError(_("Invalid PDF MIME type."))
    if detected_kind == "image" and uploaded_mime_type not in ALLOWED_EVENT_INSTANCE_IMAGE_MIME_TYPES:
        raise forms.ValidationError(_("Invalid image MIME type."))


class SubjectsToolbarForm(SharedSearch, SharedTotal):
    STATUS_RANDOMIZED_ENROLLED = "randomized_enrolled"
    STATUS_SCREENING = "screening"
    STATUS_FAIL_ELIGIBLE = "fail_eligible"

    SEARCH_FIELDS = ("subject_code", "screening_code", "randomization_code")
    TOTAL_LABEL = _("Total Subjects")

    subject_status = django_filters.ChoiceFilter(
        label=_("Subject Status"),
        choices=(
            (STATUS_RANDOMIZED_ENROLLED, _("Randomized & Enrolled")),
            (STATUS_SCREENING, _("Screening")),
            (STATUS_FAIL_ELIGIBLE, _("Fail Eligible")),
        ),
        empty_label=_("All"),
        method="filter_subject_status",
        widget=ToolbarFilterSelectWidget(
            filter_label=_("Status:"),
            aria_label=_("Filter subjects by status"),
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bind_total_field()

    @classmethod
    def filter_search(cls, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(subject_code__icontains=value)
            | Q(screening_code__icontains=value)
            | Q(randomization__randomization_number__icontains=value)
        ).distinct()

    @classmethod
    def filter_subject_status(cls, queryset, name, value):
        if value == cls.STATUS_RANDOMIZED_ENROLLED:
            return queryset.filter(
                enrollment__deleted=False,
                enrollment__is_enrolled=True,
                randomization__deleted=False,
                randomization__randomization_number__isnull=False,
            )
        if value == cls.STATUS_SCREENING:
            screening_statuses = (
                SubjectEligibilityWorkflowService.SCREENED_STATUS,
                SubjectEligibilityWorkflowService.ELIGIBLE_STATUS,
            )
            return (
                queryset.filter(
                    Q(enrollment__isnull=True)
                    | Q(
                        enrollment__deleted=False,
                        enrollment__is_enrolled=False,
                        enrollment__status__in=screening_statuses,
                    )
                )
                .exclude(
                    randomization__deleted=False,
                    randomization__randomization_number__isnull=False,
                )
            )
        if value == cls.STATUS_FAIL_ELIGIBLE:
            return queryset.filter(
                enrollment__deleted=False,
                enrollment__is_enrolled=False,
                enrollment__status=SubjectEligibilityWorkflowService.SCREEN_FAILURE_STATUS,
            )
        return queryset

    class Meta:
        model = Subject
        fields = ("subject_status", "search")
        toolbar_fields = ("subject_status", "total", "search")


class SubjectAuditHistoryFilterForm(forms.Form):
    user = forms.CharField(
        required=False,
        label=_("User"),
        widget=forms.Select(
            attrs={
                "class": "subject-audit-workbench__user-input",
                "aria-label": _("Filter audit history by user"),
                "onchange": "this.form.requestSubmit()",
            }
        ),
    )
    def __init__(self, *args, user_choices=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.set_user_choices(user_choices)

    def set_user_choices(self, user_choices):
        self.fields["user"].widget.choices = [
            ("", _("All Users")),
            *((value, value) for value in user_choices),
        ]


class SubjectEarlyTerminationForm(forms.Form):
    reason_code = forms.ChoiceField(
        label=_("Reason"),
        choices=EARLY_TERMINATION_REASON_CHOICES,
    )
    effective_at = forms.DateTimeField(
        label=_("Effective at"),
        input_formats=("%Y-%m-%dT%H:%M",),
        widget=forms.DateTimeInput(
            format="%Y-%m-%dT%H:%M",
            attrs={"type": "datetime-local"},
        ),
    )
    reason_text = forms.CharField(
        label=_("Details"),
        max_length=1000,
        widget=forms.Textarea(attrs={"rows": 3}),
    )


class SubjectIdListField(forms.Field):
    widget = forms.MultipleHiddenInput

    def clean(self, value):
        values = super().clean(value)
        if not values:
            if not self.required:
                return ()
            raise forms.ValidationError(_("Select at least one subject."))

        subject_ids = []
        seen = set()
        for value in values:
            try:
                subject_id = int(value)
            except (TypeError, ValueError) as exc:
                raise forms.ValidationError(_("Invalid subject selection.")) from exc
            if subject_id <= 0:
                raise forms.ValidationError(_("Invalid subject selection."))
            if subject_id not in seen:
                seen.add(subject_id)
                subject_ids.append(subject_id)
        if len(subject_ids) > 100:
            raise forms.ValidationError(_("Select no more than 100 subjects at a time."))
        return tuple(subject_ids)


class SubjectBulkActionForm(forms.Form):
    ACTION_DELETE = "delete"
    ACTION_RESYNC_STAGE = "resync_stage"
    ACTION_EARLY_TERMINATE = "early_terminate"
    ACTION_EXPORT_EXCEL = "export_excel"
    ACTION_CHOICES = (
        (ACTION_DELETE, _("Delete Subjects")),
        (ACTION_RESYNC_STAGE, _("Resync Stage")),
        (ACTION_EARLY_TERMINATE, _("Start Early Termination")),
        (ACTION_EXPORT_EXCEL, _("Xuất Excel đối tượng")),
    )
    SELECTION_SELECTED = "selected"
    SELECTION_FILTERED = "filtered"
    SELECTION_CHOICES = (
        (SELECTION_SELECTED, _("Selected subjects")),
        (SELECTION_FILTERED, _("All filtered subjects")),
    )

    action = forms.ChoiceField(choices=ACTION_CHOICES)
    subject_ids = SubjectIdListField(required=False)
    selection_mode = forms.ChoiceField(
        choices=SELECTION_CHOICES,
        required=False,
    )
    filter_query = forms.CharField(required=False, max_length=2000)

    def clean(self):
        cleaned_data = super().clean()
        selection_mode = (
            cleaned_data.get("selection_mode") or self.SELECTION_SELECTED
        )
        cleaned_data["selection_mode"] = selection_mode
        if (
            selection_mode == self.SELECTION_SELECTED
            and not cleaned_data.get("subject_ids")
        ):
            self.add_error(
                "subject_ids",
                _("Select at least one subject."),
            )
        return cleaned_data


class SubjectExportFieldListField(forms.Field):
    widget = forms.CheckboxSelectMultiple

    def clean(self, value):
        values = super().clean(value)
        if not values:
            raise forms.ValidationError(_("Select at least one field to export."))
        if not isinstance(values, (list, tuple)):
            values = [values]

        tokens = []
        seen = set()
        for value in values:
            token = str(value or "").strip()
            if not re.fullmatch(r"[1-9]\d*:[1-9]\d*", token):
                raise forms.ValidationError(_("Invalid export field selection."))
            if token not in seen:
                seen.add(token)
                tokens.append(token)
        if len(tokens) > 1000:
            raise forms.ValidationError(_("Select no more than 1000 fields."))
        return tuple(tokens)


class SubjectExcelExportForm(forms.Form):
    export_fields = SubjectExportFieldListField()


class SubjectPeriodOverrideForm(forms.Form):
    period_end_at = forms.DateTimeField(
        label=_("Period end at"),
        input_formats=("%Y-%m-%dT%H:%M",),
        widget=forms.DateTimeInput(
            format="%Y-%m-%dT%H:%M",
            attrs={"type": "datetime-local"},
        ),
    )
    next_period_start_at = forms.DateTimeField(
        label=_("Next period start at"),
        input_formats=("%Y-%m-%dT%H:%M",),
        widget=forms.DateTimeInput(
            format="%Y-%m-%dT%H:%M",
            attrs={"type": "datetime-local"},
        ),
    )
    reason_code = forms.ChoiceField(
        label=_("Reason"),
        choices=PERIOD_OVERRIDE_REASON_CHOICES,
    )
    reason_text = forms.CharField(
        label=_("Details"),
        max_length=1000,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    pending_data_acknowledged = forms.BooleanField(
        label=_("I acknowledge that data from the current period may remain incomplete."),
    )
    clinical_transition_confirmed = forms.BooleanField(
        label=_(
            "I confirm that the participant clinically entered the next period "
            "and the required washout was satisfied."
        ),
    )


class SubjectEventInstanceFileImportForm(forms.Form):
    import_file = forms.FileField(
        label=_("Import File"),
    )

    def clean_import_file(self):
        uploaded_file = self.cleaned_data["import_file"]
        if not uploaded_file:
            raise forms.ValidationError(_("Please choose a file to import."))
        if uploaded_file.size <= 0:
            raise forms.ValidationError(_("Uploaded file is empty."))
        if uploaded_file.size > MAX_EVENT_INSTANCE_IMPORT_FILE_SIZE_BYTES:
            raise forms.ValidationError(_("File is too large. Maximum allowed size is 10 MB."))

        extension = _validate_event_instance_upload_extension(uploaded_file)
        uploaded_mime_type = _validate_event_instance_upload_mime_type(uploaded_file)
        detected_kind = _detect_event_instance_upload_kind(uploaded_file)
        _validate_event_instance_upload_kind_consistency(
            extension=extension,
            uploaded_mime_type=uploaded_mime_type,
            detected_kind=detected_kind,
        )
        return uploaded_file
