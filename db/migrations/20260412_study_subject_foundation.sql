-- Study subject foundation schema based on the external DBML in
-- /home/trungthudo13/repositories/personal_vanguard_documents/db/dbdiagram.dbml.
-- User-related foreign keys are intentionally omitted for now because the
-- repo's DB-first chain does not yet materialize those relations consistently.

CREATE TABLE IF NOT EXISTS study_subject (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,

    subject_code VARCHAR(64) NOT NULL,

    site_id BIGINT NOT NULL,
    study_id BIGINT NOT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,

    CONSTRAINT study_subj_study_site_code_uq
        UNIQUE (study_id, site_id, subject_code),
    CONSTRAINT fk_study_subj_site
        FOREIGN KEY (site_id) REFERENCES study_site (id),
    CONSTRAINT fk_study_subj_study
        FOREIGN KEY (study_id) REFERENCES study_study (id)
);

CREATE TABLE IF NOT EXISTS study_subject_enrollment (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,

    status VARCHAR(32) NOT NULL,
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

    CONSTRAINT study_suben_subject_uq
        UNIQUE (subject_id),
    CONSTRAINT fk_study_suben_subject
        FOREIGN KEY (subject_id) REFERENCES study_subject (id),
    CONSTRAINT fk_study_suben_site
        FOREIGN KEY (site_id) REFERENCES study_site (id),
    CONSTRAINT fk_study_suben_study
        FOREIGN KEY (study_id) REFERENCES study_study (id),
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

    CONSTRAINT study_subrand_subject_uq
        UNIQUE (subject_id),
    CONSTRAINT fk_study_subrand_subject
        FOREIGN KEY (subject_id) REFERENCES study_subject (id),
    CONSTRAINT fk_study_subrand_site
        FOREIGN KEY (site_id) REFERENCES study_site (id),
    CONSTRAINT fk_study_subrand_study
        FOREIGN KEY (study_id) REFERENCES study_study (id),
    INDEX study_srand_std_site_st_ix (study_id, site_id, randomization_status),
    INDEX study_srand_st_num_ix (study_id, randomization_number)
);
