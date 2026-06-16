# Study Eligibility Assessment

`study_subject_eligibility_assessment` is the study-owned decision record for whether a subject is eligible to continue into enrollment/randomization. It stores the assessment lifecycle, result, source references, facts snapshot, failed condition summary, and audit metadata.

Eligibility criteria detail remains CRF/datacapture data. Field-specific inclusion/exclusion mappings must be configured through `datacapture_fact_mapping` or workflow seed/config data, not hard-coded into the study domain service.

Enrollment state remains in `study_subject_enrollment`. A `NOT_ELIGIBLE` assessment normally transitions the enrollment lifecycle to `ScreenFailure`; an `ELIGIBLE` assessment may transition the lifecycle to `Eligible`, but `is_enrolled` remains false until the enrollment command succeeds.

Randomization must check the latest current `FINAL` + `ELIGIBLE` assessment when the study randomization scheme requires screening pass. Missing, stale, retracted, superseded, or not-eligible assessments must block enrollment/randomization gates.
