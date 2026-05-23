import enum


class AuditEventAction:
    IDENTITY_USER_CREATED = "identity.user.created"
    IDENTITY_LOGIN_SUCCEEDED = "identity.login.succeeded"
    IDENTITY_LOGIN_FAILED = "identity.login.failed"
    IDENTITY_USER_UPDATED = "identity.user.updated"
    IDENTITY_USER_DELETED = "identity.user.deleted"
    IDENTITY_USER_RESTORED = "identity.user.restored"

    STUDY_CREATED = "study.created"
    STUDY_UPDATED = "study.updated"
    STUDY_STATUS_CHANGED = "study.status_changed"
    STUDY_DELETED = "study.deleted"
    DATACAPTURE_PAGEENTRY_CHANGE_REASONS_SUBMITTED = "datacapture.pageentry.change_reasons_submitted"


class AuditEventObjectType:
    IDENTITY_USER = "identity.user"
    IDENTITY_LOGIN_ATTEMPT = "identity.login_attempt"

    STUDY = "study"
    PAGEENTRY = "pageentry"


class AuditEventActionEnum(enum.Enum):
    STUDY_SITE_CREATED = "study.site.created"
    STUDY_SITE_UPDATED = "study.site.updated"
    STUDY_SITE_DELETED = "study.site.deleted"

    IDENTITY_USER_CHANGE_PASSWORD = "identity.user.change_password"
    IDENTITY_USER_ADMIN_SET_PASSWORD = "identity.user.admin_set_password"
    IDENTITY_USER_RESET_PASSWORD = "identity.user.reset_password"

    STUDY_RANDOMIZATION_SCHEME_INSERTED_BY_IMPORT = "study.randomization_scheme.inserted_by_import"
    STUDY_RANDOMIZATION_SCHEME_UPDATED_BY_IMPORT = "study.randomization_scheme.updated_by_import"
    STUDY_RANDOMIZATION_SCHEME_DELETED = "study.randomization_scheme.deleted"
    STUDY_RANDOMIZATION_ARM_INSERTED_BY_IMPORT = "study.randomization_arm.inserted_by_import"
    STUDY_RANDOMIZATION_ARM_UPDATED_BY_IMPORT = "study.randomization_arm.updated_by_import"
    STUDY_RANDOMIZATION_ARM_DELETED = "study.randomization_arm.deleted"
    ELIGIBILITY_ASSESSMENT_DRAFTED = "study.subject_eligibility_assessment.drafted"
    ELIGIBILITY_ASSESSMENT_FINALIZED = "study.subject_eligibility_assessment.finalized"
    ELIGIBILITY_ASSESSMENT_SUPERSEDED = "study.subject_eligibility_assessment.superseded"
    ELIGIBILITY_ASSESSMENT_RETRACTED = "study.subject_eligibility_assessment.retracted"
    ELIGIBILITY_ASSESSMENT_STALE = "study.subject_eligibility_assessment.stale"
    SUBJECT_STATUS_CHANGED_FROM_ELIGIBILITY = "study.subject_status.changed_from_eligibility"
    ENROLL_SUBJECT = "study.subject.enroll"
    ENROLL_SUBJECT_GATE_EVALUATED = "study.subject.enroll_gate_evaluated"


class AuditEventObjectTypeEnum(enum.Enum):
    STUDY_SITE = "study.site"
    IDENTITY_USER = "identity.user"

    STUDY_RANDOMIZATION_SCHEME = "study.randomization_scheme"
    STUDY_RANDOMIZATION_ARM = "study.randomization_arm"
    SUBJECT_ELIGIBILITY_ASSESSMENT = "study_subject_eligibility_assessment"
    SUBJECT_ENROLLMENT = "study_subject_enrollment"
    EVENT_GATE_EVALUATION = "study_event_gate_evaluation"
