ALTER TABLE crf_fielduiconfig
    MODIFY COLUMN control_type ENUM(
        'TEXT',
        'TEXTAREA',
        'NUMBER',
        'SELECT',
        'SELECT2',
        'RADIO',
        'CHECKBOX',
        'MULTI_SELECT',
        'DATE',
        'DATETIME',
        'LABEL_ONLY'
    ) NOT NULL;

UPDATE crf_fielduiconfig
SET options = JSON_OBJECT(
    'source',
    'static',
    'static',
    CASE
        WHEN options IS NULL OR TRIM(options) = '' THEN JSON_ARRAY()
        WHEN JSON_VALID(options) AND JSON_TYPE(options) = 'ARRAY' THEN JSON_EXTRACT(options, '$')
        WHEN JSON_VALID(options) AND JSON_TYPE(options) = 'OBJECT' THEN COALESCE(JSON_EXTRACT(options, '$.static'), JSON_ARRAY())
        ELSE JSON_ARRAY()
    END,
    'lookup',
    CASE
        WHEN JSON_VALID(options) AND JSON_TYPE(options) = 'OBJECT' THEN COALESCE(JSON_UNQUOTE(JSON_EXTRACT(options, '$.lookup')), '')
        ELSE ''
    END
)
WHERE options IS NOT NULL
  AND TRIM(options) <> ''
  AND (
      NOT JSON_VALID(options)
      OR (JSON_VALID(options) AND JSON_EXTRACT(options, '$.source') IS NULL)
  );

UPDATE crf_fielduiconfig
SET options = NULL
WHERE options IS NOT NULL
  AND TRIM(options) = '';

ALTER TABLE crf_fielduiconfig
    MODIFY COLUMN options JSON NULL;

CREATE TABLE IF NOT EXISTS crf_field_lookup (
    id BIGINT NOT NULL AUTO_INCREMENT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT(1) NOT NULL DEFAULT 0,
    `key` VARCHAR(128) NOT NULL,
    value VARCHAR(255) NOT NULL,
    label VARCHAR(255) NOT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY crf_field_lookup_key_value_uniq (`key`, value),
    KEY crf_field_lookup_key_idx (`key`),
    KEY crf_field_lookup_key_label_idx (`key`, label)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
