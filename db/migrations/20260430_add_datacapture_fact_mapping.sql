CREATE TABLE IF NOT EXISTS datacapture_fact_mapping (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    study_id BIGINT NOT NULL,
    study_version VARCHAR(20) NOT NULL,
    crf_template_id BIGINT NOT NULL,
    event_definition_id BIGINT NULL,
    field_code VARCHAR(128) NULL,
    source_path VARCHAR(512) NOT NULL,
    fact_key VARCHAR(128) NOT NULL,
    operator VARCHAR(32) NOT NULL DEFAULT 'equals',
    expected_value LONGTEXT NULL,
    value_type VARCHAR(32) NOT NULL DEFAULT 'string',
    default_value LONGTEXT NULL,
    is_enabled TINYINT NOT NULL DEFAULT 1,
    display_order INT NOT NULL DEFAULT 1,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    INDEX datacapture_fact_mapping_scope_idx (
        study_id,
        study_version,
        crf_template_id,
        is_enabled
    ),
    INDEX datacapture_fact_mapping_event_idx (
        event_definition_id,
        is_enabled
    ),
    INDEX datacapture_fact_mapping_template_fact_idx (
        crf_template_id,
        fact_key
    )
);
