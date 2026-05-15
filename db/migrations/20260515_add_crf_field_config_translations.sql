CREATE TABLE IF NOT EXISTS crf_fielddefinition_translation (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    language_code VARCHAR(15) NOT NULL,
    unit VARCHAR(50) NULL,
    codelist LONGTEXT NULL,
    comments LONGTEXT NULL,
    pattern_err_msg LONGTEXT NULL,
    field_definition_id BIGINT NOT NULL,
    UNIQUE INDEX crf_fielddefinition_translation_lang_definition_uniq (language_code, field_definition_id),
    INDEX crf_fielddefinition_translation_master_idx (field_definition_id),
    INDEX crf_fielddefinition_translation_language_idx (language_code)
);

CREATE TABLE IF NOT EXISTS crf_fielduiconfig_translation (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    language_code VARCHAR(15) NOT NULL,
    `text` LONGTEXT NULL,
    options LONGTEXT NULL,
    field_ui_config_id BIGINT NOT NULL,
    UNIQUE INDEX crf_fielduiconfig_translation_lang_config_uniq (language_code, field_ui_config_id),
    INDEX crf_fielduiconfig_translation_master_idx (field_ui_config_id),
    INDEX crf_fielduiconfig_translation_language_idx (language_code)
);
