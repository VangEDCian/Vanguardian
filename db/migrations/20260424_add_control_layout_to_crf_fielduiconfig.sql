ALTER TABLE crf_fielduiconfig
    ADD COLUMN IF NOT EXISTS control_layout ENUM('normal', 'card', 'table_row') NOT NULL DEFAULT 'normal' AFTER control_type;
