ALTER TABLE crf_fielduiconfig
    ADD COLUMN IF NOT EXISTS classes VARCHAR(255) NULL AFTER style;
