-- Align study_eventdefinition with the latest DBML and add study_event_transition_rule.
-- Source of truth:
-- /home/trungthudo13/repositories/vanguardian/documents/db/dbdiagram.dbml

ALTER TABLE study_eventdefinition
    ADD COLUMN IF NOT EXISTS event_category VARCHAR(32) NULL AFTER timing_mode,
    ADD COLUMN IF NOT EXISTS execution_mode VARCHAR(32) NOT NULL DEFAULT 'form_entry' AFTER event_category,
    DROP COLUMN IF EXISTS anchor_event_code,
    DROP COLUMN IF EXISTS day_offset,
    DROP COLUMN IF EXISTS window_before_days,
    DROP COLUMN IF EXISTS window_after_days,
    DROP COLUMN IF EXISTS opens_after_status,
    DROP INDEX IF EXISTS study_eventdefinition_version_code_uniq,
    DROP INDEX IF EXISTS study_evtdef_ver_seq_idx,
    ADD UNIQUE INDEX IF NOT EXISTS study_eventdefinition_study_version_code_uniq
        (study_id, study_version, code),
    ADD INDEX IF NOT EXISTS study_eventdefinition_study_version_sequence_idx
        (study_id, study_version, sequence_no);

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

    CONSTRAINT study_eventtransition_from_to_uniq
        UNIQUE (study_id, study_version, from_event_definition_id, to_event_definition_id),
    CONSTRAINT fk_study_eventtransition_study
        FOREIGN KEY (study_id) REFERENCES study_study (id),
    CONSTRAINT fk_study_eventtransition_from_event_definition
        FOREIGN KEY (from_event_definition_id) REFERENCES study_eventdefinition (id),
    CONSTRAINT fk_study_eventtransition_to_event_definition
        FOREIGN KEY (to_event_definition_id) REFERENCES study_eventdefinition (id),
    INDEX study_eventtransition_display_idx (study_id, study_version, display_order),
    INDEX study_eventtransition_to_enabled_idx (to_event_definition_id, is_enabled)
);
