-- Normalize study_subject code format to 3-digit sequence padding.
-- subject_code:   {study.code}-{sequence.rjust(3, "0")}
-- screening_code: {study.code}-S{sequence.rjust(3, "0")}

UPDATE study_subject AS sub
JOIN study_study AS std ON std.id = sub.study_id
SET
    sub.subject_code = CASE
        WHEN sub.subject_code IS NULL THEN NULL
        ELSE CONCAT(std.code, '-', LPAD(CAST(sub.current_sequence AS CHAR), 3, '0'))
    END,
    sub.screening_code = CASE
        WHEN sub.screening_code IS NULL THEN NULL
        ELSE CONCAT(std.code, '-S', LPAD(CAST(sub.current_sequence AS CHAR), 3, '0'))
    END
WHERE sub.current_sequence IS NOT NULL
  AND (sub.subject_code IS NOT NULL OR sub.screening_code IS NOT NULL);

