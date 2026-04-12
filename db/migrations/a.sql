-- Seed data for an open-label randomization study with:
-- - 2 treatment arms: Drug A and Drug B
-- - 60 screened subjects
-- - 44 randomized subjects after screening
-- - 22 randomized subjects per arm
-- - dose 2 starts 28 days after dose 1 (28-day washout)
--
-- Assumptions:
-- - target study already exists with id = 1
-- - actor/approver/evaluator user id = 1
-- - subject ids are represented as a generated numeric range starting from @subject_id_base + 1

START TRANSACTION;

SET @study_id := 3;
SET @actor_user_id := 1;
SET @approved_by_id := 1;
SET @evaluated_by_id := 1;
SET @subject_id_base := 1000;

SET @scheme_code := 'RAND-OPEN-AB-44';
SET @scheme_name := 'Open-label Drug A vs Drug B (44 randomized from 60 screened)';
SET @effective_from := '2026-04-10 08:00:00';

SET @existing_scheme_id := (
    SELECT id
    FROM study_randomization_scheme
    WHERE study_id = @study_id
      AND code = @scheme_code
    LIMIT 1
);

DELETE FROM study_randomization_eligibility
WHERE scheme_id = @existing_scheme_id;

DELETE FROM study_randomization_slot
WHERE scheme_id = @existing_scheme_id;

DELETE FROM study_randomization_arm
WHERE scheme_id = @existing_scheme_id;

DELETE FROM study_randomization_scheme
WHERE id = @existing_scheme_id;

INSERT INTO study_randomization_scheme (
    created_at,
    updated_at,
    study_id,
    code,
    name,
    randomization_type,
    allocation_ratio_json,
    target_randomized_total,
    eligibility_rule_code,
    requires_screening_pass,
    is_open_label,
    status,
    effective_from,
    effective_to,
    created_by_id,
    approved_by_id,
    notes
) VALUES (
    @effective_from,
    @effective_from,
    @study_id,
    @scheme_code,
    @scheme_name,
    'blocked',
    '{"A": 1, "B": 1}',
    44,
    'SCREENING_PASS_CAP_44',
    1,
    1,
    'active',
    @effective_from,
    NULL,
    @actor_user_id,
    @approved_by_id,
    'Open-label study. Screen 60 subjects, randomize 44 total with balanced 1:1 allocation (22 in arm A, 22 in arm B). Dose 2 begins 28 days after dose 1 (28-day washout).'
);

SET @scheme_id := LAST_INSERT_ID();

INSERT INTO study_randomization_arm (
    created_at,
    updated_at,
    scheme_id,
    arm_code,
    arm_name,
    target_count,
    current_count,
    display_order,
    is_active,
    notes
) VALUES
(
    @effective_from,
    @effective_from,
    @scheme_id,
    'A',
    'Drug A',
    22,
    22,
    1,
    1,
    'Open-label arm for Drug A.'
),
(
    @effective_from,
    @effective_from,
    @scheme_id,
    'B',
    'Drug B',
    22,
    22,
    2,
    1,
    'Open-label arm for Drug B.'
);

SET @arm_a_id := (
    SELECT id
    FROM study_randomization_arm
    WHERE scheme_id = @scheme_id
      AND arm_code = 'A'
    LIMIT 1
);

SET @arm_b_id := (
    SELECT id
    FROM study_randomization_arm
    WHERE scheme_id = @scheme_id
      AND arm_code = 'B'
    LIMIT 1
);

INSERT INTO study_randomization_slot (
    created_at,
    updated_at,
    scheme_id,
    arm_id,
    sequence_no,
    block_no,
    stratum_code,
    status,
    assigned_subject_id,
    assigned_event_id,
    assigned_at,
    void_reason,
    notes
)
SELECT
    DATE_ADD(@effective_from, INTERVAL seq_no - 1 MINUTE) AS created_at,
    DATE_ADD(@effective_from, INTERVAL seq_no - 1 MINUTE) AS updated_at,
    @scheme_id AS scheme_id,
    CASE WHEN MOD(seq_no, 2) = 1 THEN @arm_a_id ELSE @arm_b_id END AS arm_id,
    seq_no AS sequence_no,
    FLOOR((seq_no - 1) / 4) + 1 AS block_no,
    NULL AS stratum_code,
    'assigned' AS status,
    @subject_id_base + seq_no AS assigned_subject_id,
    NULL AS assigned_event_id,
    DATE_ADD(@effective_from, INTERVAL seq_no - 1 MINUTE) AS assigned_at,
    NULL AS void_reason,
    'Randomized after screening pass. Dose 2 planned 28 days after dose 1.' AS notes
FROM (
    SELECT ones.n + tens.n * 10 + 1 AS seq_no
    FROM (
        SELECT 0 AS n UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
        UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9
    ) AS ones
    CROSS JOIN (
        SELECT 0 AS n UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
    ) AS tens
) AS seqs
WHERE seq_no <= 44
ORDER BY seq_no;

INSERT INTO study_randomization_eligibility (
    created_at,
    updated_at,
    study_id,
    subject_id,
    scheme_id,
    is_eligible,
    evaluated_at,
    evaluated_by_id,
    reason_code,
    reason_text,
    screening_status_snapshot,
    eligibility_snapshot_json,
    notes
)
SELECT
    DATE_ADD(@effective_from, INTERVAL subj_no - 1 MINUTE) AS created_at,
    DATE_ADD(@effective_from, INTERVAL subj_no - 1 MINUTE) AS updated_at,
    @study_id AS study_id,
    @subject_id_base + subj_no AS subject_id,
    @scheme_id AS scheme_id,
    CASE WHEN subj_no <= 44 THEN 1 ELSE 0 END AS is_eligible,
    DATE_ADD(@effective_from, INTERVAL subj_no - 1 MINUTE) AS evaluated_at,
    @evaluated_by_id AS evaluated_by_id,
    CASE
        WHEN subj_no <= 44 THEN NULL
        ELSE 'SCREEN_FAIL_CAPACITY'
    END AS reason_code,
    CASE
        WHEN subj_no <= 44 THEN NULL
        ELSE 'Screened but not selected because the study caps randomization at 44 subjects.'
    END AS reason_text,
    CASE
        WHEN subj_no <= 44 THEN 'passed'
        ELSE 'passed_not_selected'
    END AS screening_status_snapshot,
    CASE
        WHEN subj_no <= 44 THEN
            CONCAT(
                '{"screening_pass":true,"selected_for_randomization":true,"planned_washout_days":28,"assigned_arm":"',
                CASE WHEN MOD(subj_no, 2) = 1 THEN 'A' ELSE 'B' END,
                '"}'
            )
        ELSE
            '{"screening_pass":true,"selected_for_randomization":false,"planned_washout_days":28,"reason":"capacity_limit_44"}'
    END AS eligibility_snapshot_json,
    CASE
        WHEN subj_no <= 44 THEN 'Eligible and selected for open-label randomization.'
        ELSE 'Passed screening but excluded because enrollment already reached the 44-subject randomization cap.'
    END AS notes
FROM (
    SELECT ones.n + tens.n * 10 + 1 AS subj_no
    FROM (
        SELECT 0 AS n UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
        UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9
    ) AS ones
    CROSS JOIN (
        SELECT 0 AS n UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
        UNION ALL SELECT 5
    ) AS tens
) AS subject_numbers
WHERE subj_no <= 60
ORDER BY subj_no;

COMMIT;
