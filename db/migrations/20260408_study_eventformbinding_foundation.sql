-- Study event form binding foundation schema.
-- Creates the design-time binding table between event definitions and CRF templates
-- based on the external DBML in
-- /home/trungthudo13/repositories/personal_vanguard_documents/db/dbdiagram.dbml.

CREATE TABLE IF NOT EXISTS study_eventformbinding (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,

    study_id BIGINT NOT NULL,
    study_version VARCHAR(20) NOT NULL,

    event_definition_id BIGINT NOT NULL,
    form_definition_id BIGINT NOT NULL,

    display_order INT NOT NULL DEFAULT 1,

    is_required TINYINT NOT NULL DEFAULT 1,
    is_enabled TINYINT NOT NULL DEFAULT 1,
    is_repeatable_within_event TINYINT NOT NULL DEFAULT 0,

    role_scope VARCHAR(64) NULL,
    entry_mode VARCHAR(32) NULL,

    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,

    CONSTRAINT study_eventformbinding_event_form_uniq
        UNIQUE (event_definition_id, form_definition_id),
    CONSTRAINT fk_study_eventformbinding_study
        FOREIGN KEY (study_id) REFERENCES study_study (id),
    CONSTRAINT fk_study_eventformbinding_event_definition
        FOREIGN KEY (event_definition_id) REFERENCES study_eventdefinition (id),
    CONSTRAINT fk_study_eventformbinding_form_definition
        FOREIGN KEY (form_definition_id) REFERENCES crf_crftemplate (id),
    INDEX study_eventformbinding_event_display_order_idx (event_definition_id, display_order)
);
