-- Study foundation schema.
-- This migration assumes identity_user already exists.

CREATE TABLE IF NOT EXISTS study_study (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,

    code VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    sponsor VARCHAR(255) NOT NULL,
    start_date DATE NULL,
    end_date DATE NULL,
    description LONGTEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,

    UNIQUE KEY study_study_code_uniq (code),

    CONSTRAINT fk_study_study_created_by
        FOREIGN KEY (created_by_id) REFERENCES identity_user (id),
    CONSTRAINT fk_study_study_updated_by
        FOREIGN KEY (updated_by_id) REFERENCES identity_user (id)
);