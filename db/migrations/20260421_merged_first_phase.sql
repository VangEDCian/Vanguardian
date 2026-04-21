-- Merged first-phase DB-first schema (up to 2026-04-21).
-- This merged file intentionally excludes SQL-level foreign keys and constraints.
-- Relationship/constraint rules are handled in Django ORM state/models.

DROP TABLE IF EXISTS crf_pagetemplate_translation;
DROP TABLE IF EXISTS crf_pagetemplate;

CREATE TABLE IF NOT EXISTS identity_user (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    `password` VARCHAR(128) NOT NULL,
    last_login DATETIME NULL,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    username VARCHAR(150) NOT NULL,
    first_name VARCHAR(150) NOT NULL DEFAULT '',
    last_name VARCHAR(150) NOT NULL DEFAULT '',
    email VARCHAR(254) NULL,
    is_staff BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    date_joined DATETIME NOT NULL,
    display_name VARCHAR(255) NOT NULL DEFAULT '',
    phone_number VARCHAR(32) NULL DEFAULT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    attempt_login TINYINT NOT NULL DEFAULT 0,
    INDEX idx_identity_user_username (username),
    INDEX idx_identity_user_email (email),
    INDEX idx_identity_user_phone_number (phone_number)
);

CREATE TABLE IF NOT EXISTS identity_user_groups (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    group_id INT NOT NULL,
    INDEX idx_identity_user_groups_user (user_id),
    INDEX idx_identity_user_groups_group (group_id),
    INDEX idx_identity_user_groups_user_group (user_id, group_id)
);

CREATE TABLE IF NOT EXISTS identity_user_user_permissions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    permission_id INT NOT NULL,
    INDEX idx_identity_user_perms_user (user_id),
    INDEX idx_identity_user_perms_permission (permission_id),
    INDEX idx_identity_user_perms_user_permission (user_id, permission_id)
);

CREATE TABLE IF NOT EXISTS identity_role (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(150) NOT NULL,
    `description` VARCHAR(255) NOT NULL DEFAULT '',
    INDEX idx_identity_role_name (name)
);

CREATE TABLE IF NOT EXISTS identity_role_groups (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    role_id BIGINT NOT NULL,
    group_id INT NOT NULL,
    INDEX idx_identity_role_groups_role (role_id),
    INDEX idx_identity_role_groups_group (group_id),
    INDEX idx_identity_role_groups_role_group (role_id, group_id)
);

CREATE TABLE IF NOT EXISTS identity_role_permissions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    role_id BIGINT NOT NULL,
    permission_id INT NOT NULL,
    INDEX idx_identity_role_permissions_role (role_id),
    INDEX idx_identity_role_permissions_permission (permission_id),
    INDEX idx_identity_role_permissions_role_permission (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS study_study (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    code VARCHAR(64) NOT NULL,
    `name` VARCHAR(255) NOT NULL,
    sponsor VARCHAR(255) NULL,
    `start_date` DATE NULL,
    end_date DATE NULL,
    `description` VARCHAR(255) NOT NULL DEFAULT '',
    is_active TINYINT NOT NULL DEFAULT 1,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    INDEX study_study_code_idx (code),
    INDEX study_study_deleted_idx (deleted),
    INDEX study_study_created_by_id_idx (created_by_id),
    INDEX study_study_deleted_created_by_id_idx (deleted, created_by_id),
    INDEX study_deleted_active_idx (deleted, is_active),
    INDEX study_deleted_start_idx (deleted, start_date),
    INDEX study_deleted_end_idx (deleted, end_date)
);

CREATE TABLE IF NOT EXISTS study_site (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    code VARCHAR(64) NOT NULL,
    `name` VARCHAR(255) NOT NULL,
    investigator VARCHAR(255) NULL,
    is_active TINYINT NOT NULL DEFAULT 1,
    study_id BIGINT NOT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    INDEX study_site_study_code_idx (study_id, code),
    INDEX study_site_deleted_idx (deleted),
    INDEX study_site_created_by_id_idx (created_by_id),
    INDEX site_study_del_creator_idx (study_id, deleted, created_by_id)
);

CREATE TABLE IF NOT EXISTS study_membership (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    user_id BIGINT NOT NULL,
    study_id BIGINT NOT NULL,
    `role` VARCHAR(64) NOT NULL,
    is_global_role TINYINT NOT NULL DEFAULT 0,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    INDEX study_membership_user_study_idx (user_id, study_id),
    INDEX study_membership_study_user_idx (study_id, user_id)
);

CREATE TABLE IF NOT EXISTS study_site_membership (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    user_id BIGINT NOT NULL,
    study_id BIGINT NOT NULL,
    site_id BIGINT NOT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    INDEX study_site_membership_user_study_site_idx (user_id, study_id, site_id),
    INDEX site_mship_study_site_user_idx (study_id, site_id, user_id)
);

CREATE TABLE IF NOT EXISTS study_eventdefinition (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    study_id BIGINT NOT NULL,
    study_version VARCHAR(20) NOT NULL,
    code VARCHAR(64) NOT NULL,
    `name` VARCHAR(255) NOT NULL,
    `description` LONGTEXT NULL,
    event_type VARCHAR(32) NOT NULL,
    timing_mode VARCHAR(32) NOT NULL DEFAULT 'scheduled',
    event_category VARCHAR(32) NULL,
    execution_mode VARCHAR(32) NOT NULL DEFAULT 'form_entry',
    sequence_no INT NOT NULL DEFAULT 1,
    phase_code VARCHAR(64) NULL,
    is_repeating TINYINT NOT NULL DEFAULT 0,
    max_repeats INT NULL,
    is_enabled TINYINT NOT NULL DEFAULT 1,
    is_required TINYINT NOT NULL DEFAULT 0,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    INDEX study_eventdefinition_study_version_code_idx (study_id, study_version, code),
    INDEX study_eventdefinition_study_version_sequence_idx (study_id, study_version, sequence_no)
);

CREATE TABLE IF NOT EXISTS study_event_transition_rule (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    study_id BIGINT NOT NULL,
    study_version VARCHAR(20) NOT NULL,
    from_event_definition_id BIGINT NOT NULL,
    to_event_definition_id BIGINT NOT NULL,
    transition_type VARCHAR(32) NOT NULL DEFAULT 'sequential',
    condition_scope VARCHAR(32) NOT NULL DEFAULT 'subject_event',
    condition_code VARCHAR(64) NULL,
    condition_expression LONGTEXT NULL,
    offset_days INT NULL,
    window_before_days INT NULL,
    window_after_days INT NULL,
    auto_open TINYINT NOT NULL DEFAULT 0,
    auto_create TINYINT NOT NULL DEFAULT 0,
    requires_previous_completion TINYINT NOT NULL DEFAULT 1,
    allow_skip TINYINT NOT NULL DEFAULT 0,
    display_order INT NOT NULL DEFAULT 1,
    is_enabled TINYINT NOT NULL DEFAULT 1,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    INDEX study_eventtransition_from_to_idx (study_id, study_version, from_event_definition_id, to_event_definition_id),
    INDEX study_eventtransition_display_idx (study_id, study_version, display_order),
    INDEX study_eventtransition_to_enabled_idx (to_event_definition_id, is_enabled)
);

CREATE TABLE IF NOT EXISTS study_eventformbinding (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    study_id BIGINT NOT NULL,
    study_version VARCHAR(20) NOT NULL,
    event_definition_id BIGINT NOT NULL,
    form_definition_id BIGINT NOT NULL,
    display_order INT NOT NULL DEFAULT 1,
    is_required TINYINT NOT NULL DEFAULT 1,
    is_enabled TINYINT NOT NULL DEFAULT 1,
    is_repeatable_within_event TINYINT NOT NULL DEFAULT 0,
    role_scope VARCHAR(64) NULL,
    entry_mode VARCHAR(32) NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    INDEX study_eventformbinding_event_form_idx (event_definition_id, form_definition_id),
    INDEX study_evtbind_evt_order_idx (event_definition_id, display_order)
);

CREATE TABLE IF NOT EXISTS study_randomization_scheme (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    study_id BIGINT NOT NULL,
    code VARCHAR(64) NOT NULL,
    `name` VARCHAR(255) NOT NULL,
    randomization_type VARCHAR(32) NOT NULL,
    allocation_ratio_json LONGTEXT NULL,
    target_randomized_total INT NOT NULL,
    eligibility_rule_code VARCHAR(64) NULL,
    requires_screening_pass TINYINT NOT NULL DEFAULT 1,
    is_open_label TINYINT NOT NULL DEFAULT 1,
    `status` VARCHAR(32) NOT NULL DEFAULT 'draft',
    effective_from DATETIME NULL,
    effective_to DATETIME NULL,
    created_by_id BIGINT NULL,
    approved_by_id BIGINT NULL,
    notes LONGTEXT NULL,
    INDEX study_randsch_study_code_idx (study_id, code),
    INDEX study_randsch_study_status_ix (study_id, status)
);

CREATE TABLE IF NOT EXISTS study_randomization_arm (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    scheme_id BIGINT NOT NULL,
    arm_code VARCHAR(32) NOT NULL,
    arm_name VARCHAR(255) NOT NULL,
    target_count INT NOT NULL,
    current_count INT NOT NULL DEFAULT 0,
    display_order INT NOT NULL DEFAULT 1,
    is_active TINYINT NOT NULL DEFAULT 1,
    notes LONGTEXT NULL,
    INDEX study_randarm_scheme_code_idx (scheme_id, arm_code),
    INDEX study_randarm_scheme_order_ix (scheme_id, display_order)
);

CREATE TABLE IF NOT EXISTS study_randomization_slot (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    scheme_id BIGINT NOT NULL,
    arm_id BIGINT NOT NULL,
    sequence_no INT NOT NULL,
    block_no INT NULL,
    stratum_code VARCHAR(64) NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'available',
    assigned_subject_id BIGINT NULL,
    assigned_event_id BIGINT NULL,
    assigned_at DATETIME NULL,
    void_reason VARCHAR(255) NULL,
    notes LONGTEXT NULL,
    INDEX study_rslot_scheme_seq_idx (scheme_id, sequence_no),
    INDEX study_rslot_scheme_status_ix (scheme_id, status),
    INDEX study_rslot_arm_status_ix (arm_id, status),
    INDEX study_rslot_subject_ix (assigned_subject_id)
);

CREATE TABLE IF NOT EXISTS study_randomization_eligibility (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    study_id BIGINT NOT NULL,
    subject_id BIGINT NOT NULL,
    scheme_id BIGINT NOT NULL,
    is_eligible TINYINT NOT NULL DEFAULT 0,
    evaluated_at DATETIME NOT NULL,
    evaluated_by_id BIGINT NULL,
    reason_code VARCHAR(64) NULL,
    reason_text VARCHAR(1000) NULL,
    screening_status_snapshot VARCHAR(64) NULL,
    eligibility_snapshot_json LONGTEXT NULL,
    notes LONGTEXT NULL,
    INDEX study_randelig_scheme_subj_ix (scheme_id, subject_id),
    INDEX study_randelig_subj_eval_ix (study_id, subject_id, evaluated_at),
    INDEX study_randelig_subj_flag_ix (subject_id, is_eligible)
);

CREATE TABLE IF NOT EXISTS study_subject (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    subject_code VARCHAR(64) NULL,
    screening_code VARCHAR(64) NULL,
    current_sequence BIGINT NOT NULL,
    site_id BIGINT NOT NULL,
    study_id BIGINT NOT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    INDEX study_subj_study_site_code_idx (study_id, site_id, subject_code),
    INDEX study_subj_study_screening_code_idx (study_id, screening_code),
    INDEX study_subj_study_sequence_idx (study_id, current_sequence)
);

CREATE TABLE IF NOT EXISTS study_subject_enrollment (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    `status` VARCHAR(32) NOT NULL,
    status_datetime DATETIME NULL,
    status_reason_code VARCHAR(64) NULL,
    status_reason_text LONGTEXT NULL,
    is_enrolled TINYINT NOT NULL DEFAULT 0,
    enrollment_date DATE NULL,
    enrolled_by_id BIGINT NULL,
    screen_failed_at DATETIME NULL,
    withdrawn_at DATETIME NULL,
    subject_id BIGINT NOT NULL,
    site_id BIGINT NOT NULL,
    study_id BIGINT NOT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    INDEX study_suben_subject_idx (subject_id),
    INDEX study_suben_std_site_st_ix (study_id, site_id, status),
    INDEX study_suben_study_enr_ix (study_id, is_enrolled)
);

CREATE TABLE IF NOT EXISTS study_subject_randomization (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    randomization_status VARCHAR(16) NULL,
    randomization_datetime DATETIME NULL,
    randomization_sequence VARCHAR(64) NULL,
    randomization_number VARCHAR(64) NULL,
    randomization_source VARCHAR(16) NULL,
    randomized_by_id BIGINT NULL,
    subject_id BIGINT NOT NULL,
    site_id BIGINT NOT NULL,
    study_id BIGINT NOT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    INDEX study_subrand_subject_idx (subject_id),
    INDEX study_srand_std_site_st_ix (study_id, site_id, randomization_status),
    INDEX study_srand_st_num_ix (study_id, randomization_number)
);

CREATE TABLE IF NOT EXISTS study_eventinstance (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    study_id BIGINT NOT NULL,
    subject_id BIGINT NOT NULL,
    event_definition_id BIGINT NOT NULL,
    study_version VARCHAR(20) NOT NULL,
    repeat_index INT NOT NULL DEFAULT 1,
    planned_date DATETIME NULL,
    target_date DATETIME NULL,
    actual_date DATETIME NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'not_ready',
    opened_at DATETIME NULL,
    completed_at DATETIME NULL,
    verified_at DATETIME NULL,
    locked_at DATETIME NULL,
    opened_by_id BIGINT NULL,
    completed_by_id BIGINT NULL,
    verified_by_id BIGINT NULL,
    locked_by_id BIGINT NULL,
    skip_reason LONGTEXT NULL,
    cancel_reason LONGTEXT NULL,
    event_code_snapshot VARCHAR(64) NULL,
    event_name_snapshot VARCHAR(255) NULL,
    event_type_snapshot VARCHAR(32) NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    INDEX study_eventinstance_subject_event_repeat_idx (subject_id, event_definition_id, repeat_index),
    INDEX study_eventinstance_study_subject_idx (study_id, subject_id),
    INDEX study_eventinstance_subject_status_idx (subject_id, status),
    INDEX study_eventinstance_planned_date_idx (planned_date),
    INDEX study_eventinstance_actual_date_idx (actual_date)
);

CREATE TABLE IF NOT EXISTS crf_crftemplate (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    code VARCHAR(64) NOT NULL,
    `version` VARCHAR(32) NOT NULL,
    is_active TINYINT NOT NULL DEFAULT 1,
    study_id BIGINT NOT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    INDEX crf_crftemplate_study_code_version_idx (study_id, code, version)
);

CREATE TABLE IF NOT EXISTS crf_crftemplate_translation (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    language_code VARCHAR(15) NOT NULL,
    `name` VARCHAR(255) NOT NULL,
    crf_template_id BIGINT NOT NULL,
    INDEX crf_crftemplate_translation_lang_template_idx (language_code, crf_template_id),
    INDEX crf_crftemplate_translation_master_idx (crf_template_id),
    INDEX crf_crftemplate_translation_language_idx (language_code)
);

CREATE TABLE IF NOT EXISTS crf_sectiontemplate (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    crf_template_id BIGINT NOT NULL,
    section_code VARCHAR(64) NOT NULL,
    display_order INT NOT NULL DEFAULT 1,
    is_required TINYINT NOT NULL DEFAULT 1,
    is_enabled TINYINT NOT NULL DEFAULT 1,
    is_repeatable TINYINT NOT NULL DEFAULT 0,
    min_repeats INT NOT NULL DEFAULT 0,
    max_repeats INT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    INDEX crf_sectiontemplate_crf_template_section_code_idx (crf_template_id, section_code),
    INDEX crf_sectiontemplate_crf_template_display_order_idx (crf_template_id, display_order)
);

CREATE TABLE IF NOT EXISTS crf_sectiontemplate_translation (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    language_code VARCHAR(15) NOT NULL,
    section_name VARCHAR(255) NOT NULL,
    `description` TEXT NULL,
    help_text TEXT NULL,
    instruction_text TEXT NULL,
    section_template_id BIGINT NOT NULL,
    INDEX crf_sectiontemplate_translation_lang_section_idx (language_code, section_template_id),
    INDEX crf_sectiontemplate_translation_master_idx (section_template_id),
    INDEX crf_sectiontemplate_translation_language_idx (language_code)
);

CREATE TABLE IF NOT EXISTS crf_section_layoutconfig (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    section_template_id BIGINT NOT NULL,
    layout_type VARCHAR(32) NOT NULL DEFAULT 'section',
    column_count INT NOT NULL DEFAULT 1,
    label_position VARCHAR(16) NOT NULL DEFAULT 'top',
    density VARCHAR(16) NOT NULL DEFAULT 'standard',
    section_style VARCHAR(32) NOT NULL DEFAULT 'plain',
    is_collapsible TINYINT NOT NULL DEFAULT 0,
    is_expanded_by_default TINYINT NOT NULL DEFAULT 1,
    show_section_header TINYINT NOT NULL DEFAULT 1,
    show_border TINYINT NOT NULL DEFAULT 0,
    show_background TINYINT NOT NULL DEFAULT 0,
    custom_css_class VARCHAR(128) NULL,
    custom_layout_schema JSON NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    INDEX crf_section_layoutconfig_section_template_idx (section_template_id)
);

CREATE TABLE IF NOT EXISTS crf_fieldtemplate (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    field_key VARCHAR(100) NOT NULL,
    data_type VARCHAR(20) NOT NULL,
    is_active TINYINT NOT NULL DEFAULT 1,
    crf_template_id BIGINT NOT NULL,
    section_template_id BIGINT NULL,
    display_order INT NOT NULL DEFAULT 1,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    INDEX crf_fieldtemplate_crf_template_fieldkey_idx (crf_template_id, field_key),
    INDEX crf_fieldtemplate_section_display_order_idx (section_template_id, display_order)
);

CREATE TABLE IF NOT EXISTS crf_fieldtemplate_translation (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    language_code VARCHAR(15) NOT NULL,
    label LONGTEXT NOT NULL,
    field_template_id BIGINT NOT NULL,
    INDEX crf_fieldtemplate_translation_lang_field_idx (language_code, field_template_id),
    INDEX crf_fieldtemplate_translation_master_idx (field_template_id),
    INDEX crf_fieldtemplate_translation_language_idx (language_code)
);

CREATE TABLE IF NOT EXISTS crf_fielddefinition (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    sdtm LONGTEXT NULL,
    unit VARCHAR(50) NULL,
    range_min DECIMAL(21, 6) NULL,
    range_max DECIMAL(21, 6) NULL,
    `precision` INT NULL,
    allowed_missing_values LONGTEXT NOT NULL,
    codelist LONGTEXT NULL,
    data_semantic LONGTEXT NULL,
    comments LONGTEXT NULL,
    text_max_length INT NULL,
    text_min_length INT NULL,
    pattern LONGTEXT NULL,
    pattern_err_msg LONGTEXT NULL,
    field_template_id BIGINT NOT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    INDEX crf_fielddefinition_field_template_idx (field_template_id)
);

CREATE TABLE IF NOT EXISTS crf_fielduiconfig (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    control_type VARCHAR(50) NOT NULL,
    layout LONGTEXT NULL,
    `text` LONGTEXT NULL,
    behavior LONGTEXT NULL,
    options LONGTEXT NULL,
    style LONGTEXT NULL,
    field_template_id BIGINT NOT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    INDEX crf_fielduiconfig_field_template_idx (field_template_id)
);

CREATE TABLE IF NOT EXISTS crf_fieldvalidationrule (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    rule_type VARCHAR(64) NOT NULL,
    expression LONGTEXT NOT NULL,
    severity VARCHAR(20) NOT NULL,
    mode VARCHAR(20) NOT NULL,
    field_template_id BIGINT NOT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    INDEX crf_fieldvalidationrule_field_template_idx (field_template_id)
);

CREATE TABLE IF NOT EXISTS crf_fieldvalidationrule_translation (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    language_code VARCHAR(15) NOT NULL,
    `message` LONGTEXT NOT NULL,
    field_validation_rule_id BIGINT NOT NULL,
    INDEX crf_fieldvalidationrule_translation_lang_rule_idx (language_code, field_validation_rule_id),
    INDEX crf_fieldvalidationrule_translation_master_idx (field_validation_rule_id),
    INDEX crf_fieldvalidationrule_translation_language_idx (language_code)
);

CREATE TABLE IF NOT EXISTS audit_auditevent (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    `action` VARCHAR(64) NOT NULL,
    object_type VARCHAR(64) NOT NULL,
    object_id VARCHAR(64) NOT NULL,
    before_data LONGTEXT NOT NULL,
    after_data LONGTEXT NOT NULL,
    ip_address CHAR(39) NULL,
    user_agent VARCHAR(255) NOT NULL,
    user_id BIGINT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    INDEX audit_auditevent_obj_time_idx (object_type, object_id, created_at)
);
