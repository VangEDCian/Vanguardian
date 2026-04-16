-- Make study_subject.subject_code nullable and add screening_code.
-- Source of truth:
-- /home/trungthudo13/repositories/vanguardian/documents/db/dbdiagram.dbml

ALTER TABLE study_subject
    MODIFY COLUMN subject_code VARCHAR(64) NULL,
    ADD COLUMN IF NOT EXISTS screening_code VARCHAR(64) NULL AFTER subject_code;

UPDATE study_subject AS sub
JOIN study_study AS std ON std.id = sub.study_id
SET sub.screening_code = CONCAT(
    std.code,
    '-S',
    LPAD(CAST(sub.current_sequence AS CHAR), 3, '0')
)
WHERE sub.screening_code IS NULL;

ALTER TABLE study_subject
    ADD UNIQUE INDEX IF NOT EXISTS study_subj_study_screening_code_uq (study_id, screening_code);
