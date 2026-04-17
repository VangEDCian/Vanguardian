-- Remove CRF page template layer and migrate references to CRF template.

SET @schema_name = DATABASE();

ALTER TABLE crf_fieldtemplate
    ADD COLUMN IF NOT EXISTS crf_template_id BIGINT NULL;

SET @has_crf_pagetemplate = (
    SELECT COUNT(*)
    FROM information_schema.tables
    WHERE table_schema = @schema_name
      AND table_name = 'crf_pagetemplate'
);

SET @sql_text = IF(
    @has_crf_pagetemplate > 0,
    'UPDATE crf_fieldtemplate AS ft JOIN crf_pagetemplate AS pt ON pt.id = ft.page_template_id SET ft.crf_template_id = pt.crf_template_id WHERE ft.crf_template_id IS NULL',
    'SELECT 1'
);
PREPARE stmt FROM @sql_text;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @old_fk_name = (
    SELECT kcu.CONSTRAINT_NAME
    FROM information_schema.KEY_COLUMN_USAGE AS kcu
    WHERE kcu.TABLE_SCHEMA = @schema_name
      AND kcu.TABLE_NAME = 'crf_fieldtemplate'
      AND kcu.COLUMN_NAME = 'page_template_id'
      AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
    LIMIT 1
);
SET @sql_text = IF(
    @old_fk_name IS NULL,
    'SELECT 1',
    CONCAT('ALTER TABLE crf_fieldtemplate DROP FOREIGN KEY ', @old_fk_name)
);
PREPARE stmt FROM @sql_text;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_old_unique = (
    SELECT COUNT(*)
    FROM information_schema.statistics AS s
    WHERE s.TABLE_SCHEMA = @schema_name
      AND s.TABLE_NAME = 'crf_fieldtemplate'
      AND s.INDEX_NAME = 'crf_fieldtemplate_page_fieldkey_uniq'
);
SET @sql_text = IF(
    @has_old_unique > 0,
    'ALTER TABLE crf_fieldtemplate DROP INDEX crf_fieldtemplate_page_fieldkey_uniq',
    'SELECT 1'
);
PREPARE stmt FROM @sql_text;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

ALTER TABLE crf_fieldtemplate
    DROP COLUMN IF EXISTS page_template_id;

SET @null_crf_template_id_count = (
    SELECT COUNT(*)
    FROM crf_fieldtemplate
    WHERE crf_template_id IS NULL
);
SET @sql_text = IF(
    @null_crf_template_id_count = 0,
    'ALTER TABLE crf_fieldtemplate MODIFY COLUMN crf_template_id BIGINT NOT NULL',
    'SELECT 1'
);
PREPARE stmt FROM @sql_text;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_new_unique = (
    SELECT COUNT(*)
    FROM information_schema.statistics AS s
    WHERE s.TABLE_SCHEMA = @schema_name
      AND s.TABLE_NAME = 'crf_fieldtemplate'
      AND s.INDEX_NAME = 'crf_fieldtemplate_crf_template_fieldkey_uniq'
);
SET @sql_text = IF(
    @has_new_unique = 0,
    'ALTER TABLE crf_fieldtemplate ADD CONSTRAINT crf_fieldtemplate_crf_template_fieldkey_uniq UNIQUE (crf_template_id, field_key)',
    'SELECT 1'
);
PREPARE stmt FROM @sql_text;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_new_fk = (
    SELECT COUNT(*)
    FROM information_schema.KEY_COLUMN_USAGE AS kcu
    WHERE kcu.TABLE_SCHEMA = @schema_name
      AND kcu.TABLE_NAME = 'crf_fieldtemplate'
      AND kcu.COLUMN_NAME = 'crf_template_id'
      AND kcu.REFERENCED_TABLE_NAME = 'crf_crftemplate'
);
SET @sql_text = IF(
    @has_new_fk = 0,
    'ALTER TABLE crf_fieldtemplate ADD CONSTRAINT fk_crf_fieldtemplate_crf_template FOREIGN KEY (crf_template_id) REFERENCES crf_crftemplate (id)',
    'SELECT 1'
);
PREPARE stmt FROM @sql_text;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

DROP TABLE IF EXISTS crf_pagetemplate_translation;
DROP TABLE IF EXISTS crf_pagetemplate;
