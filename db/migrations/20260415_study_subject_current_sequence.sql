-- Add current_sequence to study_subject to support sequential subject creation
-- per study, aligned with:
-- /home/trungthudo13/repositories/vanguardian/documents/db/dbdiagram.dbml

ALTER TABLE study_subject
    ADD COLUMN IF NOT EXISTS current_sequence BIGINT NULL AFTER subject_code;
-- Data backfill moved to:
-- db/seeders/20260415_study_subject_current_sequence.sql

ALTER TABLE study_subject
    MODIFY COLUMN current_sequence BIGINT NOT NULL,
    ADD UNIQUE INDEX IF NOT EXISTS study_subj_study_sequence_uq (study_id, current_sequence);
