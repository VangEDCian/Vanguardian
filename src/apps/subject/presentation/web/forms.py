from pathlib import Path

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.shared.filters import SharedSearch, SharedTotal
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
    SEARCH_FIELDS = ("subject_code", "screening_code")
    TOTAL_LABEL = _("Total Subjects")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bind_total_field()

    class Meta:
        model = Subject
        fields = ("search",)
        toolbar_fields = ("total", "search")


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
