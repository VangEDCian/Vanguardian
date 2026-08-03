from django import forms
from django.utils.translation import gettext_lazy as _

from apps.study.application.subject_identifier_policy import (
    DEFAULT_SCREENING_CODE_PATTERN,
    DEFAULT_SUBJECT_CODE_PATTERN,
    ScreeningIdentifierMode,
    StudySubjectIdentifierPolicy,
    SubjectCodeUniquenessScope,
    SubjectIdentifierMode,
    SubjectIdentifierPolicyError,
)


class StudyForm(forms.Form):
    code = forms.CharField(
        max_length=64,
        label=_("Study Code"),
        widget=forms.TextInput(attrs={"placeholder": _("e.g. STUDY-001")}),
    )
    name = forms.CharField(
        max_length=255,
        label=_("Study Name"),
        widget=forms.TextInput(attrs={"placeholder": _("e.g. REACT-AF Phase II")}),
    )
    sponsor = forms.CharField(
        max_length=255,
        required=False,
        label=_("Sponsor"),
        widget=forms.TextInput(attrs={"placeholder": _("e.g. Acme Pharma")}),
    )
    start_date = forms.DateField(
        required=False,
        label=_("Start Date"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_date = forms.DateField(
        required=False,
        label=_("End Date"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    description = forms.CharField(
        max_length=255,
        required=False,
        label=_("Description"),
        widget=forms.TextInput(attrs={"placeholder": _("Enter study description...")}),
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Active"),
    )
    subject_identifier_mode = forms.ChoiceField(
        label=_("Subject Code Assignment"),
        choices=(
            (SubjectIdentifierMode.GENERATED_AT_SCREENING, _("Generate at screening")),
            (SubjectIdentifierMode.GENERATED_AT_ENROLLMENT, _("Generate at enrollment")),
            (
                SubjectIdentifierMode.COPY_RANDOMIZATION_AT_RANDOMIZATION,
                _("Copy Randomization Code at randomization"),
            ),
            (SubjectIdentifierMode.EXTERNAL, _("Supply externally")),
        ),
        initial=SubjectIdentifierMode.GENERATED_AT_ENROLLMENT,
    )
    screening_identifier_mode = forms.ChoiceField(
        label=_("Screening Code Assignment"),
        choices=(
            (ScreeningIdentifierMode.GENERATED, _("Generate at screening")),
            (ScreeningIdentifierMode.EXTERNAL, _("Supply externally")),
            (ScreeningIdentifierMode.DISABLED, _("Disabled")),
        ),
        initial=ScreeningIdentifierMode.GENERATED,
    )
    subject_code_pattern = forms.CharField(
        max_length=128,
        label=_("Subject Code Pattern"),
        initial=DEFAULT_SUBJECT_CODE_PATTERN,
        help_text=_(
            "Used only for generated Subject Codes. Allowed placeholders: "
            "{study_code}, {site_code}, {sequence}."
        ),
    )
    screening_code_pattern = forms.CharField(
        max_length=128,
        label=_("Screening Code Pattern"),
        initial=DEFAULT_SCREENING_CODE_PATTERN,
        help_text=_(
            "Used only for generated Screening Codes. Allowed placeholders: "
            "{study_code}, {site_code}, {sequence}."
        ),
    )
    subject_code_uniqueness_scope = forms.ChoiceField(
        label=_("Subject Code Uniqueness"),
        choices=(
            (SubjectCodeUniquenessScope.STUDY_SITE, _("Within study and site")),
            (SubjectCodeUniquenessScope.STUDY, _("Across the whole study")),
        ),
        initial=SubjectCodeUniquenessScope.STUDY_SITE,
    )
    lock_subject_code_after_assignment = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Lock Subject Code after assignment"),
    )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date and end_date < start_date:
            self.add_error("end_date", _("End date must be on or after start date."))
        try:
            StudySubjectIdentifierPolicy(
                study_id=0,
                study_code=cleaned_data.get("code") or "STUDY",
                subject_identifier_mode=cleaned_data.get("subject_identifier_mode"),
                screening_identifier_mode=cleaned_data.get("screening_identifier_mode"),
                subject_code_pattern=cleaned_data.get("subject_code_pattern"),
                screening_code_pattern=cleaned_data.get("screening_code_pattern"),
                subject_code_uniqueness_scope=cleaned_data.get(
                    "subject_code_uniqueness_scope"
                ),
                lock_subject_code_after_assignment=bool(
                    cleaned_data.get("lock_subject_code_after_assignment")
                ),
            ).validate()
        except SubjectIdentifierPolicyError as exc:
            self.add_error(None, str(exc))
        return cleaned_data
