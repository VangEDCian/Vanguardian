-- Make study_subject.subject_code nullable and add screening_code.
-- Source of truth:
-- /home/trungthudo13/repositories/vanguardian/documents/db/dbdiagram.dbml

ALTER TABLE study_subject
    MODIFY COLUMN subject_code VARCHAR(64) NULL,
    ADD COLUMN IF NOT EXISTS screening_code VARCHAR(64) NULL AFTER subject_code;
-- Data backfill moved to:
-- db/seeders/20260416_study_subject_screening_subject_nullable.sql

ALTER TABLE study_subject
    ADD UNIQUE INDEX IF NOT EXISTS study_subj_study_screening_code_uq (study_id, screening_code);
