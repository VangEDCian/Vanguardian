-- Add current_sequence to study_subject to support sequential subject creation
-- per study, aligned with:
-- /home/trungthudo13/repositories/vanguardian/documents/db/dbdiagram.dbml

ALTER TABLE study_subject
    ADD COLUMN IF NOT EXISTS current_sequence BIGINT NULL AFTER subject_code;

UPDATE study_subject AS target
JOIN (
    SELECT pending.id,
           pending.study_id,
           base.max_current_sequence + pending.study_rank AS generated_sequence
    FROM (
        SELECT s.id,
               s.study_id,
               ROW_NUMBER() OVER (PARTITION BY s.study_id ORDER BY s.id) AS study_rank
        FROM study_subject AS s
        WHERE s.current_sequence IS NULL
    ) AS pending
    JOIN (
        SELECT s.study_id,
               COALESCE(MAX(s.current_sequence), 0) AS max_current_sequence
        FROM study_subject AS s
        GROUP BY s.study_id
    ) AS base ON base.study_id = pending.study_id
) AS to_fill ON to_fill.id = target.id
SET target.current_sequence = to_fill.generated_sequence
WHERE target.current_sequence IS NULL;

ALTER TABLE study_subject
    MODIFY COLUMN current_sequence BIGINT NOT NULL,
    ADD UNIQUE INDEX IF NOT EXISTS study_subj_study_sequence_uq (study_id, current_sequence);

