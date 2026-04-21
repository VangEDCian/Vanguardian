-- CRF section template foundation.
-- Adds section-level template tables and schema updates.
-- Data backfill (INSERT/UPDATE) is extracted to:
-- db/seeders/20260421_crf_sectiontemplate_foundation.sql

SET @schema_name = DATABASE();

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

    CONSTRAINT crf_sectiontemplate_crf_template_section_code_uniq
        UNIQUE (crf_template_id, section_code),
    INDEX crf_sectiontemplate_crf_template_display_order_idx (crf_template_id, display_order),
    CONSTRAINT fk_crf_sectiontemplate_crf_template
        FOREIGN KEY (crf_template_id) REFERENCES crf_crftemplate (id)
);

CREATE TABLE IF NOT EXISTS crf_sectiontemplate_translation (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    language_code VARCHAR(15) NOT NULL,

    section_name VARCHAR(255) NOT NULL,
    description TEXT NULL,
    help_text TEXT NULL,
    instruction_text TEXT NULL,

    section_template_id BIGINT NOT NULL,

    CONSTRAINT crf_sectiontemplate_translation_lang_section_uniq
        UNIQUE (language_code, section_template_id),
    CONSTRAINT fk_crf_sectiontemplate_translation_master
        FOREIGN KEY (section_template_id) REFERENCES crf_sectiontemplate (id),
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

    CONSTRAINT crf_section_layoutconfig_section_template_uniq
        UNIQUE (section_template_id),
    CONSTRAINT fk_crf_section_layoutconfig_section_template
        FOREIGN KEY (section_template_id) REFERENCES crf_sectiontemplate (id)
);

ALTER TABLE crf_fieldtemplate
    ADD COLUMN IF NOT EXISTS display_order INT NOT NULL DEFAULT 1;

ALTER TABLE crf_fieldtemplate
    ADD COLUMN IF NOT EXISTS section_template_id BIGINT NULL;

SET @null_section_template_id_count = (
    SELECT COUNT(*)
    FROM crf_fieldtemplate
    WHERE section_template_id IS NULL
);
SET @sql_text = IF(
    @null_section_template_id_count = 0,
    'ALTER TABLE crf_fieldtemplate MODIFY COLUMN section_template_id BIGINT NOT NULL',
    'DO 1'
);
PREPARE stmt FROM @sql_text;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_section_display_order_idx = (
    SELECT COUNT(*)
    FROM information_schema.statistics AS s
    WHERE s.TABLE_SCHEMA = @schema_name
      AND s.TABLE_NAME = 'crf_fieldtemplate'
      AND s.INDEX_NAME = 'crf_fieldtemplate_section_display_order_idx'
);
SET @sql_text = IF(
    @has_section_display_order_idx = 0,
    'ALTER TABLE crf_fieldtemplate ADD INDEX crf_fieldtemplate_section_display_order_idx (section_template_id, display_order)',
    'DO 1'
);
PREPARE stmt FROM @sql_text;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_section_template_fk = (
    SELECT COUNT(*)
    FROM information_schema.KEY_COLUMN_USAGE AS kcu
    WHERE kcu.TABLE_SCHEMA = @schema_name
      AND kcu.TABLE_NAME = 'crf_fieldtemplate'
      AND kcu.COLUMN_NAME = 'section_template_id'
      AND kcu.REFERENCED_TABLE_NAME = 'crf_sectiontemplate'
);
SET @sql_text = IF(
    @has_section_template_fk = 0,
    'ALTER TABLE crf_fieldtemplate ADD CONSTRAINT fk_crf_fieldtemplate_section_template FOREIGN KEY (section_template_id) REFERENCES crf_sectiontemplate (id)',
    'DO 1'
);
PREPARE stmt FROM @sql_text;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
