-- Study foundation schema.
-- This migration creates the study owner aggregate and site child table
-- based on db/dbdiagram.dbml.

CREATE TABLE IF NOT EXISTS study_study (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    code VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    sponsor VARCHAR(255) NULL,
    start_date DATE NULL,
    end_date DATE NULL,
    description VARCHAR(255) NOT NULL DEFAULT '',
    is_active TINYINT NOT NULL DEFAULT 1,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    CONSTRAINT uq_study_study_code UNIQUE (code),
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
    name VARCHAR(255) NOT NULL,
    investigator VARCHAR(255) NULL,
    is_active TINYINT NOT NULL DEFAULT 1,
    study_id BIGINT NOT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    CONSTRAINT uq_study_site_study_code UNIQUE (study_id, code),
    CONSTRAINT fk_study_site_study
        FOREIGN KEY (study_id) REFERENCES study_study (id),
    INDEX study_study_deleted_idx (deleted),
    INDEX study_study_created_by_id_idx (created_by_id),
    INDEX study_study_deleted_created_by_id_idx (study_id, deleted, created_by_id)
);
