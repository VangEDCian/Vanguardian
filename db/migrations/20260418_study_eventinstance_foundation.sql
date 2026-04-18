-- Study event instance foundation schema based on the external DBML in
-- /Users/trungthudo/Documents/repositories/Vanguardian.Documents/db/dbdiagram.dbml.
-- User-related foreign keys are intentionally omitted for now because the
-- repo's DB-first chain does not yet materialize those relations consistently.

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

    status VARCHAR(32) NOT NULL DEFAULT 'not_ready',

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

    CONSTRAINT study_eventinstance_subject_event_repeat_uniq
        UNIQUE (subject_id, event_definition_id, repeat_index),
    CONSTRAINT fk_study_eventinstance_study
        FOREIGN KEY (study_id) REFERENCES study_study (id),
    CONSTRAINT fk_study_eventinstance_subject
        FOREIGN KEY (subject_id) REFERENCES study_subject (id),
    CONSTRAINT fk_study_eventinstance_event_definition
        FOREIGN KEY (event_definition_id) REFERENCES study_eventdefinition (id),
    INDEX study_eventinstance_study_subject_idx (study_id, subject_id),
    INDEX study_eventinstance_subject_status_idx (subject_id, status),
    INDEX study_eventinstance_planned_date_idx (planned_date),
    INDEX study_eventinstance_actual_date_idx (actual_date)
);
