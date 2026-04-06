-- Study event definition foundation schema.
-- Creates the design-time event definition table based on the external DBML
-- in /home/trungthudo13/repositories/personal_vanguard_documents/db/dbdiagram.dbml
-- and mirrors the local db/dbdiagram.dbml mapping.

CREATE TABLE IF NOT EXISTS study_eventdefinition (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,

    study_id BIGINT NOT NULL,
    study_version_id BIGINT NOT NULL,

    code VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description LONGTEXT NULL,

    event_type VARCHAR(32) NOT NULL,
    timing_mode VARCHAR(32) NOT NULL DEFAULT 'scheduled',

    sequence_no INT NOT NULL DEFAULT 1,
    phase_code VARCHAR(64) NULL,

    is_repeating TINYINT NOT NULL DEFAULT 0,
    max_repeats INT NULL,

    is_enabled TINYINT NOT NULL DEFAULT 1,
    is_required TINYINT NOT NULL DEFAULT 0,

    anchor_event_code VARCHAR(64) NULL,
    day_offset INT NULL,
    window_before_days INT NULL,
    window_after_days INT NULL,

    opens_after_status VARCHAR(64) NULL,

    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,

    CONSTRAINT study_evtdef_ver_code_uniq
        UNIQUE (study_version_id, code),
    CONSTRAINT fk_study_eventdefinition_study
        FOREIGN KEY (study_id) REFERENCES study_study (id),
    INDEX study_evtdef_studyver_seq_idx (study_id, study_version_id, sequence_no)
);
