-- Study randomization foundation schema.
-- Creates scheme, arm, slot, and eligibility tables based on the external DBML in
-- /home/trungthudo13/repositories/personal_vanguard_documents/db/dbdiagram.dbml.
-- Physical FKs to study_subject and study_randomization_event are intentionally
-- omitted for now because those tables do not yet have SQL foundation migrations
-- in this repo's DB-first chain.

CREATE TABLE IF NOT EXISTS study_randomization_scheme (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,

    study_id BIGINT NOT NULL,

    code VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,

    randomization_type VARCHAR(32) NOT NULL,
    allocation_ratio_json LONGTEXT NULL,

    target_randomized_total INT NOT NULL,
    eligibility_rule_code VARCHAR(64) NULL,
    requires_screening_pass TINYINT NOT NULL DEFAULT 1,
    is_open_label TINYINT NOT NULL DEFAULT 1,

    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    effective_from DATETIME NULL,
    effective_to DATETIME NULL,

    created_by_id BIGINT NULL,
    approved_by_id BIGINT NULL,

    notes LONGTEXT NULL,

    CONSTRAINT study_randsch_study_code_uq
        UNIQUE (study_id, code),
    CONSTRAINT fk_study_randsch_study
        FOREIGN KEY (study_id) REFERENCES study_study (id),
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

    CONSTRAINT study_randarm_scheme_code_uq
        UNIQUE (scheme_id, arm_code),
    CONSTRAINT fk_study_randarm_scheme
        FOREIGN KEY (scheme_id) REFERENCES study_randomization_scheme (id),
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

    status VARCHAR(32) NOT NULL DEFAULT 'available',
    assigned_subject_id BIGINT NULL,
    assigned_event_id BIGINT NULL,
    assigned_at DATETIME NULL,

    void_reason VARCHAR(255) NULL,
    notes LONGTEXT NULL,

    CONSTRAINT study_rslot_scheme_seq_uq
        UNIQUE (scheme_id, sequence_no),
    CONSTRAINT fk_study_rslot_scheme
        FOREIGN KEY (scheme_id) REFERENCES study_randomization_scheme (id),
    CONSTRAINT fk_study_rslot_arm
        FOREIGN KEY (arm_id) REFERENCES study_randomization_arm (id),
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

    CONSTRAINT fk_study_randelig_study
        FOREIGN KEY (study_id) REFERENCES study_study (id),
    CONSTRAINT fk_study_randelig_scheme
        FOREIGN KEY (scheme_id) REFERENCES study_randomization_scheme (id),
    INDEX study_randelig_scheme_subj_ix (scheme_id, subject_id),
    INDEX study_randelig_subj_eval_ix (study_id, subject_id, evaluated_at),
    INDEX study_randelig_subj_flag_ix (subject_id, is_eligible)
);
