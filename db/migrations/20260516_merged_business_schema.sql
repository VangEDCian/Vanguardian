-- Merged business SQL migrations through 2026-05-16.
-- Source files were concatenated in lexical order to preserve migration behavior.
-- Do not keep the split source files in db/migrations/ together with this file,
-- because the README apply loop runs every db/migrations/*.sql file.

-- ============================================================================
-- Source: 20260421_merged_first_phase.sql
-- ============================================================================

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


-- ============================================================================
-- Source: 20260423_add_classes_to_crf_fielduiconfig.sql
-- ============================================================================

ALTER TABLE crf_fielduiconfig
    ADD COLUMN IF NOT EXISTS classes VARCHAR(255) NULL AFTER style;


-- ============================================================================
-- Source: 20260424_add_control_layout_to_crf_fielduiconfig.sql
-- ============================================================================

ALTER TABLE crf_fielduiconfig
    ADD COLUMN IF NOT EXISTS control_layout ENUM('normal', 'card', 'table_row') NOT NULL DEFAULT 'normal' AFTER control_type;


-- ============================================================================
-- Source: 20260424_convert_control_type_to_enum.sql
-- ============================================================================

UPDATE crf_fielduiconfig
SET control_type = CASE
    WHEN control_type IS NULL OR TRIM(control_type) = '' THEN 'LABEL_ONLY'
    WHEN UPPER(TRIM(control_type)) IN (
        'TEXT',
        'TEXTAREA',
        'NUMBER',
        'SELECT',
        'RADIO',
        'CHECKBOX',
        'MULTI_SELECT',
        'DATE',
        'DATETIME',
        'LABEL_ONLY'
    ) THEN UPPER(TRIM(control_type))
    WHEN LOWER(TRIM(control_type)) IN ('entry box', 'textbox', 'text box') THEN 'TEXT'
    WHEN LOWER(TRIM(control_type)) = 'text area' THEN 'TEXTAREA'
    WHEN LOWER(TRIM(control_type)) IN ('dropdown list', 'dropdown') THEN 'SELECT'
    WHEN LOWER(TRIM(control_type)) = 'radio button list' THEN 'RADIO'
    WHEN LOWER(TRIM(control_type)) = 'checkbox list' THEN 'CHECKBOX'
    WHEN LOWER(TRIM(control_type)) = 'date picker' THEN 'DATE'
    WHEN LOWER(TRIM(control_type)) = 'time picker' THEN 'DATETIME'
    WHEN LOWER(TRIM(control_type)) IN ('calculated field', 'calculated') THEN 'LABEL_ONLY'
    ELSE 'LABEL_ONLY'
END;

ALTER TABLE crf_fielduiconfig
    MODIFY COLUMN control_type ENUM(
        'TEXT',
        'TEXTAREA',
        'NUMBER',
        'SELECT',
        'RADIO',
        'CHECKBOX',
        'MULTI_SELECT',
        'DATE',
        'DATETIME',
        'LABEL_ONLY'
    ) NOT NULL;


-- ============================================================================
-- Source: 20260429_add_datacapture_page_tables.sql
-- ============================================================================

CREATE TABLE IF NOT EXISTS datacapture_pagestate (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    status VARCHAR(16) NOT NULL,
    final_data LONGTEXT NOT NULL,
    verified_at DATETIME NULL,
    locked_at DATETIME NULL,
    crf_template_id BIGINT NOT NULL,
    subject_id BIGINT NOT NULL,
    visit_id BIGINT NOT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    verified_by_id BIGINT NULL,
    locked_by_id BIGINT NULL,
    UNIQUE INDEX datacapture_pagestate_subject_visit_crf_uniq (subject_id, visit_id, crf_template_id)
);

CREATE TABLE IF NOT EXISTS datacapture_pageentry (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    entry_no INT NOT NULL,
    entry_kind VARCHAR(16) NOT NULL,
    entry_version VARCHAR(16) NOT NULL,
    data LONGTEXT NOT NULL,
    status VARCHAR(16) NOT NULL,
    crf_template_id BIGINT NOT NULL,
    subject_id BIGINT NOT NULL,
    visit_id BIGINT NOT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    INDEX datacapture_pageentry_subject_visit_crf_version_idx (
        subject_id,
        visit_id,
        crf_template_id,
        entry_version
    )
);


-- ============================================================================
-- Source: 20260430_add_datacapture_fact_mapping.sql
-- ============================================================================

CREATE TABLE IF NOT EXISTS datacapture_fact_mapping (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    study_id BIGINT NOT NULL,
    study_version VARCHAR(20) NOT NULL,
    crf_template_id BIGINT NOT NULL,
    event_definition_id BIGINT NULL,
    field_code VARCHAR(128) NULL,
    source_path VARCHAR(512) NOT NULL,
    fact_key VARCHAR(128) NOT NULL,
    operator VARCHAR(32) NOT NULL DEFAULT 'equals',
    expected_value LONGTEXT NULL,
    value_type VARCHAR(32) NOT NULL DEFAULT 'string',
    default_value LONGTEXT NULL,
    is_enabled TINYINT NOT NULL DEFAULT 1,
    display_order INT NOT NULL DEFAULT 1,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    INDEX datacapture_fact_mapping_scope_idx (
        study_id,
        study_version,
        crf_template_id,
        is_enabled
    ),
    INDEX datacapture_fact_mapping_event_idx (
        event_definition_id,
        is_enabled
    ),
    INDEX datacapture_fact_mapping_template_fact_idx (
        crf_template_id,
        fact_key
    )
);


-- ============================================================================
-- Source: 20260430_add_study_eventinstance_transition_log.sql
-- ============================================================================

CREATE TABLE IF NOT EXISTS study_eventinstance_transition_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    study_id BIGINT NOT NULL,
    subject_id BIGINT NOT NULL,
    source_event_instance_id BIGINT NOT NULL,
    target_event_instance_id BIGINT NULL,
    transition_rule_id BIGINT NULL,
    from_event_definition_id BIGINT NOT NULL,
    to_event_definition_id BIGINT NULL,
    from_status VARCHAR(32) NOT NULL,
    to_status VARCHAR(32) NOT NULL,
    trigger_source VARCHAR(64) NOT NULL DEFAULT 'system',
    result VARCHAR(32) NOT NULL DEFAULT 'applied',
    reason VARCHAR(128) NULL,
    facts_json LONGTEXT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    INDEX study_evtins_trlog_study_subject_created_idx (study_id, subject_id, created_at),
    INDEX study_evtins_trlog_source_created_idx (source_event_instance_id, created_at),
    INDEX study_evtins_trlog_target_created_idx (target_event_instance_id, created_at),
    INDEX study_evtins_trlog_rule_created_idx (transition_rule_id, created_at)
);


-- ============================================================================
-- Source: 20260502_add_identity_user_roles.sql
-- ============================================================================

CREATE TABLE IF NOT EXISTS identity_user_roles (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    INDEX idx_identity_user_roles_user (user_id),
    INDEX idx_identity_user_roles_role (role_id),
    UNIQUE INDEX idx_identity_user_roles_user_role (user_id, role_id)
);


-- ============================================================================
-- Source: 20260502_set_identity_user_is_staff_default_true.sql
-- ============================================================================

ALTER TABLE identity_user
    MODIFY COLUMN is_staff BOOLEAN NOT NULL DEFAULT TRUE;

CREATE TABLE IF NOT EXISTS `study_eventinstance_file` (
    `id` bigint NOT NULL AUTO_INCREMENT,
    `created_at` datetime(6) NOT NULL,
    `updated_at` datetime(6) NOT NULL,
    `deleted` tinyint(1) NOT NULL DEFAULT 0,
    `study_id` bigint NOT NULL,
    `subject_id` bigint NOT NULL,
    `site_id` bigint NOT NULL,
    `event_instance_id` bigint NOT NULL,
    `original_file_name` varchar(512) NOT NULL,
    `stored_file_name` varchar(512) NOT NULL,
    `storage_relative_path` varchar(1024) NOT NULL,
    `mime_type` varchar(128) NULL,
    `file_size_bytes` bigint NOT NULL,
    `checksum_sha256` varchar(64) NULL,
    `created_by_id` bigint NULL,
    `updated_by_id` bigint NULL,
    PRIMARY KEY (`id`),
    KEY `seif_evt_del_cr_idx` (`event_instance_id`, `deleted`, `created_at`),
    KEY `seif_st_sub_del_idx` (`study_id`, `subject_id`, `deleted`),
    KEY `seif_checksum_idx` (`checksum_sha256`),
    CONSTRAINT `seif_study_fk` FOREIGN KEY (`study_id`) REFERENCES `study_study` (`id`),
    CONSTRAINT `seif_subject_fk` FOREIGN KEY (`subject_id`) REFERENCES `study_subject` (`id`),
    CONSTRAINT `seif_site_fk` FOREIGN KEY (`site_id`) REFERENCES `study_site` (`id`),
    CONSTRAINT `seif_event_instance_fk` FOREIGN KEY (`event_instance_id`) REFERENCES `study_eventinstance` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Source: 20260512_datacapture_pagestate_final_data_nullable.sql
-- ============================================================================

-- final_data is reserved for post-submit verification metadata (e.g. __form_verification__);
-- capture payloads live on datacapture_pageentry.data. New rows start with NULL until verified.
ALTER TABLE datacapture_pagestate MODIFY COLUMN final_data LONGTEXT NULL;


-- ============================================================================
-- Source: 20260513_add_reconcile_dataquery.sql
-- ============================================================================

CREATE TABLE IF NOT EXISTS reconcile_dataquery (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    status VARCHAR(16) NOT NULL,
    source VARCHAR(16) NOT NULL,
    question_text LONGTEXT NOT NULL,
    resolution_note VARCHAR(255) NULL,
    closed_at DATETIME NULL,
    page_state_id BIGINT NOT NULL,
    field_template_id BIGINT NULL,
    validation_rule_id BIGINT NULL,
    assigned_to_id BIGINT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    INDEX idx_reconcile_dataquery_page_state (page_state_id),
    INDEX idx_reconcile_dataquery_field_template (field_template_id),
    INDEX idx_reconcile_dataquery_validation_rule (validation_rule_id),
    INDEX idx_reconcile_dataquery_status (status),
    INDEX idx_reconcile_dataquery_source (source)
);


-- ============================================================================
-- Source: 20260514_add_governance_lock_tables.sql
-- ============================================================================

CREATE TABLE IF NOT EXISTS governance_databaselock (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    status VARCHAR(16) NOT NULL DEFAULT 'locked',
    level VARCHAR(32) NOT NULL DEFAULT 'database',
    reason LONGTEXT NULL,
    locked_at DATETIME NOT NULL,
    unlocked_at DATETIME NULL,
    locked_by_id BIGINT NULL,
    unlocked_by_id BIGINT NULL,
    INDEX governance_databaselock_status_idx (status, level, deleted),
    INDEX governance_databaselock_locked_at_idx (locked_at)
);

CREATE TABLE IF NOT EXISTS governance_lockrecord (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    status VARCHAR(16) NOT NULL DEFAULT 'locked',
    level VARCHAR(32) NOT NULL DEFAULT 'page',
    reason LONGTEXT NULL,
    subject_id BIGINT NULL,
    visit_id BIGINT NULL,
    crf_template_id BIGINT NULL,
    page_state_id BIGINT NULL,
    locked_at DATETIME NOT NULL,
    unlocked_at DATETIME NULL,
    locked_by_id BIGINT NULL,
    unlocked_by_id BIGINT NULL,
    INDEX governance_lockrecord_scope_idx (subject_id, visit_id, crf_template_id, status, deleted),
    INDEX governance_lockrecord_page_state_idx (page_state_id, status, deleted),
    INDEX governance_lockrecord_locked_at_idx (locked_at)
);


-- ============================================================================
-- Source: 20260514_update_datacapture_fieldreview_unique_index.sql
-- ============================================================================

ALTER TABLE datacapture_fieldreview
DROP INDEX datacapture_fieldreview_page_field_type_uniq;

ALTER TABLE datacapture_fieldreview
ADD UNIQUE INDEX datacapture_fieldreview_page_field_type_uniq (
  page_state_id,
  field_template_id,
  review_type,
  data_version
);


-- ============================================================================
-- Source: 20260514_update_datacapture_page_workflow.sql
-- ============================================================================

UPDATE datacapture_pagestate
SET status = 'in_progress'
WHERE status = 'draft';

UPDATE datacapture_pagestate
SET status = 'under_review'
WHERE status = 'in_review';

UPDATE datacapture_pagestate
SET status = 'not_started'
WHERE status = 'canceled';

UPDATE datacapture_pageentry
SET status = 'cancelled'
WHERE status = 'canceled';

UPDATE datacapture_pagestate
SET final_data = '{}'
WHERE final_data IS NULL;

ALTER TABLE datacapture_pagestate MODIFY COLUMN status VARCHAR(32) NOT NULL;
ALTER TABLE datacapture_pagestate MODIFY COLUMN final_data LONGTEXT NOT NULL;
ALTER TABLE datacapture_pagestate ADD COLUMN IF NOT EXISTS data_version INT NOT NULL DEFAULT 1;
ALTER TABLE datacapture_pagestate ADD COLUMN IF NOT EXISTS current_entry_id BIGINT NULL;
ALTER TABLE datacapture_pagestate ADD COLUMN IF NOT EXISTS submitted_at DATETIME NULL;
ALTER TABLE datacapture_pagestate ADD COLUMN IF NOT EXISTS review_started_at DATETIME NULL;
ALTER TABLE datacapture_pagestate ADD COLUMN IF NOT EXISTS finalized_at DATETIME NULL;
ALTER TABLE datacapture_pagestate ADD COLUMN IF NOT EXISTS verified_data_version INT NULL;
ALTER TABLE datacapture_pagestate ADD COLUMN IF NOT EXISTS locked_data_version INT NULL;
ALTER TABLE datacapture_pagestate ADD COLUMN IF NOT EXISTS finalized_data_version INT NULL;
ALTER TABLE datacapture_pagestate ADD COLUMN IF NOT EXISTS submitted_by_id BIGINT NULL;
ALTER TABLE datacapture_pagestate ADD COLUMN IF NOT EXISTS review_started_by_id BIGINT NULL;
ALTER TABLE datacapture_pagestate ADD COLUMN IF NOT EXISTS finalized_by_id BIGINT NULL;

ALTER TABLE datacapture_pagestate ADD INDEX IF NOT EXISTS datacapture_pagestate_subject_status_idx (subject_id, status);
ALTER TABLE datacapture_pagestate ADD INDEX IF NOT EXISTS datacapture_pagestate_visit_status_idx (visit_id, status);
ALTER TABLE datacapture_pagestate ADD INDEX IF NOT EXISTS datacapture_pagestate_crf_status_idx (crf_template_id, status);

ALTER TABLE datacapture_pageentry MODIFY COLUMN status VARCHAR(32) NOT NULL;
ALTER TABLE datacapture_pageentry ADD COLUMN IF NOT EXISTS page_state_id BIGINT NULL;
ALTER TABLE datacapture_pageentry ADD COLUMN IF NOT EXISTS parent_entry_id BIGINT NULL;
ALTER TABLE datacapture_pageentry ADD COLUMN IF NOT EXISTS submitted_at DATETIME NULL;
ALTER TABLE datacapture_pageentry ADD COLUMN IF NOT EXISTS accepted_at DATETIME NULL;
ALTER TABLE datacapture_pageentry ADD COLUMN IF NOT EXISTS rejected_at DATETIME NULL;
ALTER TABLE datacapture_pageentry ADD COLUMN IF NOT EXISTS rejection_reason LONGTEXT NULL;
ALTER TABLE datacapture_pageentry ADD COLUMN IF NOT EXISTS correction_reason LONGTEXT NULL;
ALTER TABLE datacapture_pageentry ADD COLUMN IF NOT EXISTS submitted_by_id BIGINT NULL;
ALTER TABLE datacapture_pageentry ADD COLUMN IF NOT EXISTS accepted_by_id BIGINT NULL;
ALTER TABLE datacapture_pageentry ADD COLUMN IF NOT EXISTS rejected_by_id BIGINT NULL;

UPDATE datacapture_pageentry pe
JOIN datacapture_pagestate ps
  ON ps.subject_id = pe.subject_id
 AND ps.visit_id = pe.visit_id
 AND ps.crf_template_id = pe.crf_template_id
SET pe.page_state_id = ps.id
WHERE pe.page_state_id IS NULL;

ALTER TABLE datacapture_pageentry MODIFY COLUMN page_state_id BIGINT NOT NULL;
ALTER TABLE datacapture_pageentry ADD UNIQUE INDEX IF NOT EXISTS datacapture_pageentry_pagestate_version_uniq (page_state_id, entry_version);
ALTER TABLE datacapture_pageentry ADD INDEX IF NOT EXISTS datacapture_pageentry_pagestate_status_idx (page_state_id, status);

CREATE TABLE IF NOT EXISTS datacapture_fieldreview (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    page_state_id BIGINT NOT NULL,
    field_template_id BIGINT NOT NULL,
    review_type VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    data_version INT NOT NULL,
    value_snapshot LONGTEXT NULL,
    reviewed_at DATETIME NULL,
    verified_at DATETIME NULL,
    reason_code VARCHAR(64) NULL,
    reason_text LONGTEXT NULL,
    reviewed_by_id BIGINT NULL,
    verified_by_id BIGINT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    UNIQUE INDEX datacapture_fieldreview_page_field_type_uniq (page_state_id, field_template_id, review_type),
    INDEX datacapture_fieldreview_page_status_idx (page_state_id, status),
    INDEX datacapture_fieldreview_field_status_idx (field_template_id, status),
    INDEX datacapture_fieldreview_page_version_idx (page_state_id, data_version)
);

CREATE TABLE IF NOT EXISTS datacapture_pagestate_transition_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    page_state_id BIGINT NOT NULL,
    from_status VARCHAR(32) NULL,
    to_status VARCHAR(32) NOT NULL,
    data_version INT NULL,
    reason_code VARCHAR(64) NULL,
    reason_text LONGTEXT NULL,
    trigger_source VARCHAR(32) NOT NULL,
    actor_id BIGINT NULL,
    facts_json LONGTEXT NULL,
    INDEX datacapture_pagestate_trlog_page_time_idx (page_state_id, created_at),
    INDEX datacapture_pagestate_trlog_page_status_idx (page_state_id, to_status)
);

ALTER TABLE reconcile_dataquery MODIFY COLUMN status VARCHAR(32) NOT NULL;
ALTER TABLE reconcile_dataquery MODIFY COLUMN resolution_note VARCHAR(1000) NULL;
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS query_type VARCHAR(32) NOT NULL DEFAULT 'manual';
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS severity VARCHAR(16) NOT NULL DEFAULT 'minor';
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS is_blocking TINYINT NOT NULL DEFAULT 1;
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS opened_at DATETIME NULL;
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS answered_at DATETIME NULL;
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS resolved_at DATETIME NULL;
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS reason_code VARCHAR(64) NULL;
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS page_entry_id BIGINT NULL;
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS data_version INT NULL;
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS field_path VARCHAR(512) NULL;
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS value_snapshot LONGTEXT NULL;
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS opened_by_id BIGINT NULL;
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS answered_by_id BIGINT NULL;
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS resolved_by_id BIGINT NULL;
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS closed_by_id BIGINT NULL;

UPDATE reconcile_dataquery
SET opened_at = created_at
WHERE opened_at IS NULL;

UPDATE reconcile_dataquery
SET opened_by_id = created_by_id
WHERE opened_by_id IS NULL;

ALTER TABLE reconcile_dataquery MODIFY COLUMN opened_at DATETIME NOT NULL;
ALTER TABLE reconcile_dataquery ADD INDEX IF NOT EXISTS reconcile_dataquery_page_status_idx (page_state_id, status);
ALTER TABLE reconcile_dataquery ADD INDEX IF NOT EXISTS reconcile_dataquery_page_blocking_status_idx (page_state_id, is_blocking, status);
ALTER TABLE reconcile_dataquery ADD INDEX IF NOT EXISTS reconcile_dataquery_field_status_idx (field_template_id, status);
ALTER TABLE reconcile_dataquery ADD INDEX IF NOT EXISTS reconcile_dataquery_assignee_status_idx (assigned_to_id, status);

CREATE TABLE IF NOT EXISTS crf_fieldreview_policy (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    study_id BIGINT NOT NULL,
    study_version VARCHAR(20) NOT NULL,
    crf_template_id BIGINT NOT NULL,
    field_template_id BIGINT NOT NULL,
    review_type VARCHAR(32) NOT NULL,
    is_required_for_page_verify TINYINT NOT NULL DEFAULT 0,
    is_required_for_lock TINYINT NOT NULL DEFAULT 0,
    is_blocking_if_missing TINYINT NOT NULL DEFAULT 1,
    role_required VARCHAR(64) NULL,
    is_enabled TINYINT NOT NULL DEFAULT 1,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    UNIQUE INDEX crf_fieldreview_policy_scope_uniq (
        study_id,
        study_version,
        crf_template_id,
        field_template_id,
        review_type
    ),
    INDEX crf_fieldreview_policy_crf_enabled_idx (crf_template_id, is_enabled),
    INDEX crf_fieldreview_policy_field_type_idx (field_template_id, review_type)
);


-- ============================================================================
-- Source: 20260515_add_crf_field_config_translations.sql
-- ============================================================================

CREATE TABLE IF NOT EXISTS crf_fielddefinition_translation (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    language_code VARCHAR(15) NOT NULL,
    unit VARCHAR(50) NULL,
    codelist LONGTEXT NULL,
    comments LONGTEXT NULL,
    pattern_err_msg LONGTEXT NULL,
    field_definition_id BIGINT NOT NULL,
    UNIQUE INDEX crf_fielddefinition_translation_lang_definition_uniq (language_code, field_definition_id),
    INDEX crf_fdtr_master_idx (field_definition_id),
    INDEX crf_fdtr_lang_idx (language_code)
);

CREATE TABLE IF NOT EXISTS crf_fielduiconfig_translation (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    language_code VARCHAR(15) NOT NULL,
    `text` LONGTEXT NULL,
    options LONGTEXT NULL,
    field_ui_config_id BIGINT NOT NULL,
    UNIQUE INDEX crf_fielduiconfig_translation_lang_config_uniq (language_code, field_ui_config_id),
    INDEX crf_fuictr_master_idx (field_ui_config_id),
    INDEX crf_fuictr_lang_idx (language_code)
);


-- ============================================================================
-- Source: 20260515_add_select2_field_lookup.sql
-- ============================================================================

ALTER TABLE crf_fielduiconfig
    MODIFY COLUMN control_type ENUM(
        'TEXT',
        'TEXTAREA',
        'NUMBER',
        'SELECT',
        'SELECT2',
        'RADIO',
        'CHECKBOX',
        'MULTI_SELECT',
        'DATE',
        'DATETIME',
        'LABEL_ONLY'
    ) NOT NULL;

UPDATE crf_fielduiconfig
SET options = JSON_OBJECT(
    'source',
    'static',
    'static',
    CASE
        WHEN options IS NULL OR TRIM(options) = '' THEN JSON_ARRAY()
        WHEN JSON_VALID(options) AND JSON_TYPE(options) = 'ARRAY' THEN JSON_EXTRACT(options, '$')
        WHEN JSON_VALID(options) AND JSON_TYPE(options) = 'OBJECT' THEN COALESCE(JSON_EXTRACT(options, '$.static'), JSON_ARRAY())
        ELSE JSON_ARRAY()
    END,
    'lookup',
    CASE
        WHEN JSON_VALID(options) AND JSON_TYPE(options) = 'OBJECT' THEN COALESCE(JSON_UNQUOTE(JSON_EXTRACT(options, '$.lookup')), '')
        ELSE ''
    END
)
WHERE options IS NOT NULL
  AND TRIM(options) <> ''
  AND (
      NOT JSON_VALID(options)
      OR (JSON_VALID(options) AND JSON_EXTRACT(options, '$.source') IS NULL)
  );

UPDATE crf_fielduiconfig
SET options = NULL
WHERE options IS NOT NULL
  AND TRIM(options) = '';

ALTER TABLE crf_fielduiconfig
    MODIFY COLUMN options JSON NULL;

CREATE TABLE IF NOT EXISTS crf_field_lookup (
    id BIGINT NOT NULL AUTO_INCREMENT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    `key` VARCHAR(128) NOT NULL,
    value VARCHAR(255) NOT NULL,
    label VARCHAR(255) NOT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY crf_field_lookup_key_value_uniq (`key`, value),
    KEY crf_field_lookup_key_idx (`key`),
    KEY crf_field_lookup_key_label_idx (`key`, label)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================================
-- Source: 20260516_drop_crf_translated_config_columns.sql
-- ============================================================================

ALTER TABLE crf_fielddefinition
    DROP COLUMN IF EXISTS unit,
    DROP COLUMN IF EXISTS codelist,
    DROP COLUMN IF EXISTS comments,
    DROP COLUMN IF EXISTS pattern_err_msg;

ALTER TABLE crf_fielduiconfig
    DROP COLUMN IF EXISTS `text`,
    DROP COLUMN IF EXISTS options;


