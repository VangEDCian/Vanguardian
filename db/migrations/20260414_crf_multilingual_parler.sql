-- CRF multilingual support for django-parler.
-- Moves translated business text out of the shared CRF tables into dedicated
-- translation tables so the Django state can use parler while the schema
-- remains DB-first.

CREATE TABLE IF NOT EXISTS crf_crftemplate_translation (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    language_code VARCHAR(15) NOT NULL,
    `name` VARCHAR(255) NOT NULL,
    crf_template_id BIGINT NOT NULL,

    CONSTRAINT crf_crftemplate_translation_lang_template_uniq
        UNIQUE (language_code, crf_template_id),
    CONSTRAINT fk_crf_crftemplate_translation_master
        FOREIGN KEY (crf_template_id) REFERENCES crf_crftemplate (id),
    INDEX crf_crftemplate_translation_master_idx (crf_template_id),
    INDEX crf_crftemplate_translation_language_idx (language_code)
);

-- INSERT INTO crf_crftemplate_translation (language_code, `name`, crf_template_id)
-- SELECT 'en', t.`name`, t.id
-- FROM crf_crftemplate AS t
-- WHERE NOT EXISTS (
--     SELECT 1
--     FROM crf_crftemplate_translation AS tt
--     WHERE tt.language_code = 'en'
--       AND tt.crf_template_id = t.id
-- );

CREATE TABLE IF NOT EXISTS crf_fieldtemplate_translation (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    language_code VARCHAR(15) NOT NULL,
    label LONGTEXT NOT NULL,
    field_template_id BIGINT NOT NULL,

    CONSTRAINT crf_fieldtemplate_translation_lang_field_uniq
        UNIQUE (language_code, field_template_id),
    CONSTRAINT fk_crf_fieldtemplate_translation_master
        FOREIGN KEY (field_template_id) REFERENCES crf_fieldtemplate (id),
    INDEX crf_fieldtemplate_translation_master_idx (field_template_id),
    INDEX crf_fieldtemplate_translation_language_idx (language_code)
);

-- INSERT INTO crf_fieldtemplate_translation (language_code, label, field_template_id)
-- SELECT 'en', t.label, t.id
-- FROM crf_fieldtemplate AS t
-- WHERE NOT EXISTS (
--     SELECT 1
--     FROM crf_fieldtemplate_translation AS tt
--     WHERE tt.language_code = 'en'
--       AND tt.field_template_id = t.id
-- );

CREATE TABLE IF NOT EXISTS crf_fieldvalidationrule_translation (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    language_code VARCHAR(15) NOT NULL,
    `message` LONGTEXT NOT NULL,
    field_validation_rule_id BIGINT NOT NULL,

    CONSTRAINT crf_fieldvalidationrule_translation_lang_rule_uniq
        UNIQUE (language_code, field_validation_rule_id),
    CONSTRAINT fk_crf_fieldvalidationrule_translation_master
        FOREIGN KEY (field_validation_rule_id) REFERENCES crf_fieldvalidationrule (id),
    INDEX crf_fieldvalidationrule_translation_master_idx (field_validation_rule_id),
    INDEX crf_fieldvalidationrule_translation_language_idx (language_code)
);

-- INSERT INTO crf_fieldvalidationrule_translation (language_code, `message`, field_validation_rule_id)
-- SELECT 'en', t.`message`, t.id
-- FROM crf_fieldvalidationrule AS t
-- WHERE NOT EXISTS (
--     SELECT 1
--     FROM crf_fieldvalidationrule_translation AS tt
--     WHERE tt.language_code = 'en'
--       AND tt.field_validation_rule_id = t.id
-- );

ALTER TABLE crf_crftemplate
    DROP COLUMN IF EXISTS `name`;

ALTER TABLE crf_fieldtemplate
    DROP COLUMN IF EXISTS label;

ALTER TABLE crf_fieldvalidationrule
    DROP COLUMN IF EXISTS `message`;
