-- CRF foundation schema.
-- Creates the CRF design tables currently mapped in src/apps/study/infrastructure/persistence/models.py
-- and reflected in db/dbdiagram.dbml.

CREATE TABLE IF NOT EXISTS crf_crftemplate (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,

    code VARCHAR(64) NOT NULL,
    `name` VARCHAR(255) NOT NULL,
    `version` VARCHAR(32) NOT NULL,
    is_active TINYINT NOT NULL DEFAULT 1,

    study_id BIGINT NOT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,

    CONSTRAINT crf_crftemplate_study_code_version_uniq
        UNIQUE (study_id, code, `version`),
    CONSTRAINT fk_crf_crftemplate_study
        FOREIGN KEY (study_id) REFERENCES study_study (id)
);

CREATE TABLE IF NOT EXISTS crf_pagetemplate (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,

    code VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    `order` INT NOT NULL,

    crf_template_id BIGINT NOT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,

    CONSTRAINT crf_pagetemplate_crf_template_code_uniq
        UNIQUE (crf_template_id, code),
    CONSTRAINT fk_crf_pagetemplate_crf_template
        FOREIGN KEY (crf_template_id) REFERENCES crf_crftemplate (id)
);

CREATE TABLE IF NOT EXISTS crf_fieldtemplate (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,

    field_key VARCHAR(100) NOT NULL,
    label VARCHAR(500) NOT NULL,
    data_type VARCHAR(20) NOT NULL,
    is_active TINYINT NOT NULL DEFAULT 1,

    page_template_id BIGINT NOT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,

    CONSTRAINT crf_fieldtemplate_page_fieldkey_uniq
        UNIQUE (page_template_id, field_key),
    CONSTRAINT fk_crf_fieldtemplate_page_template
        FOREIGN KEY (page_template_id) REFERENCES crf_pagetemplate (id)
);

CREATE TABLE IF NOT EXISTS crf_fielddefinition (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,

    sdtm VARCHAR(500) NULL,
    unit VARCHAR(50) NULL,
    range_min DECIMAL(21, 6) NULL,
    range_max DECIMAL(21, 6) NULL,
    `precision` INT NULL,
    allowed_missing_values VARCHAR(500) NOT NULL,
    codelist VARCHAR(500) NOT NULL,
    data_semantic VARCHAR(500) NULL,
    comments VARCHAR(500) NULL,
    text_max_length INT NULL,
    text_min_length INT NULL,
    pattern VARCHAR(500) NULL,
    pattern_err_msg VARCHAR(500) NULL,

    field_template_id BIGINT NOT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,

    CONSTRAINT crf_fielddefinition_field_template_uniq
        UNIQUE (field_template_id),
    CONSTRAINT fk_crf_fielddefinition_field_template
        FOREIGN KEY (field_template_id) REFERENCES crf_fieldtemplate (id)
);

CREATE TABLE IF NOT EXISTS crf_fielduiconfig (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,

    control_type VARCHAR(50) NOT NULL,
    layout VARCHAR(500) NULL,
    `text` VARCHAR(500) NULL,
    behavior VARCHAR(500) NULL,
    options VARCHAR(500) NULL,
    style VARCHAR(500) NULL,

    field_template_id BIGINT NOT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,

    CONSTRAINT crf_fielduiconfig_field_template_uniq
        UNIQUE (field_template_id),
    CONSTRAINT fk_crf_fielduiconfig_field_template
        FOREIGN KEY (field_template_id) REFERENCES crf_fieldtemplate (id)
);

CREATE TABLE IF NOT EXISTS crf_fieldvalidationrule (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,

    rule_type VARCHAR(64) NOT NULL,
    expression VARCHAR(500) NOT NULL,
    `message` VARCHAR(500) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    mode VARCHAR(20) NOT NULL,

    field_template_id BIGINT NOT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,

    CONSTRAINT fk_crf_fieldvalidationrule_field_template
        FOREIGN KEY (field_template_id) REFERENCES crf_fieldtemplate (id)
);
