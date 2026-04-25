UPDATE crf_fielduiconfig
SET control_type = CASE
    WHEN control_type IS NULL OR TRIM(control_type) = '' THEN 'LABEL_ONLY'
    WHEN UPPER(TRIM(control_type)) IN (
        'TEXT',
        'TEXTAREA',
        'NUMBER',
        'SELECT',
        'RADIO',
        'CHECKBOX',
        'MULTI_SELECT',
        'DATE',
        'DATETIME',
        'LABEL_ONLY'
    ) THEN UPPER(TRIM(control_type))
    WHEN LOWER(TRIM(control_type)) IN ('entry box', 'textbox', 'text box') THEN 'TEXT'
    WHEN LOWER(TRIM(control_type)) = 'text area' THEN 'TEXTAREA'
    WHEN LOWER(TRIM(control_type)) IN ('dropdown list', 'dropdown') THEN 'SELECT'
    WHEN LOWER(TRIM(control_type)) = 'radio button list' THEN 'RADIO'
    WHEN LOWER(TRIM(control_type)) = 'checkbox list' THEN 'CHECKBOX'
    WHEN LOWER(TRIM(control_type)) = 'date picker' THEN 'DATE'
    WHEN LOWER(TRIM(control_type)) = 'time picker' THEN 'DATETIME'
    WHEN LOWER(TRIM(control_type)) IN ('calculated field', 'calculated') THEN 'LABEL_ONLY'
    ELSE 'LABEL_ONLY'
END;

ALTER TABLE crf_fielduiconfig
    MODIFY COLUMN control_type ENUM(
        'TEXT',
        'TEXTAREA',
        'NUMBER',
        'SELECT',
        'RADIO',
        'CHECKBOX',
        'MULTI_SELECT',
        'DATE',
        'DATETIME',
        'LABEL_ONLY'
    ) NOT NULL;
