-- Make crf_fielddefinition.codelist nullable (DB-first).

ALTER TABLE crf_fielddefinition
    MODIFY COLUMN codelist LONGTEXT NULL;
