UPDATE datacapture_pagestate
SET status = 'in_progress'
WHERE status = 'draft';

UPDATE datacapture_pagestate
SET status = 'under_review'
WHERE status = 'in_review';

UPDATE datacapture_pagestate
SET status = 'not_started'
WHERE status = 'canceled';

UPDATE datacapture_pageentry
SET status = 'cancelled'
WHERE status = 'canceled';

UPDATE datacapture_pagestate
SET final_data = '{}'
WHERE final_data IS NULL;

ALTER TABLE datacapture_pagestate MODIFY COLUMN status VARCHAR(32) NOT NULL;
ALTER TABLE datacapture_pagestate MODIFY COLUMN final_data LONGTEXT NOT NULL;
ALTER TABLE datacapture_pagestate ADD COLUMN IF NOT EXISTS data_version INT NOT NULL DEFAULT 1;
ALTER TABLE datacapture_pagestate ADD COLUMN IF NOT EXISTS current_entry_id BIGINT NULL;
ALTER TABLE datacapture_pagestate ADD COLUMN IF NOT EXISTS submitted_at DATETIME NULL;
ALTER TABLE datacapture_pagestate ADD COLUMN IF NOT EXISTS review_started_at DATETIME NULL;
ALTER TABLE datacapture_pagestate ADD COLUMN IF NOT EXISTS finalized_at DATETIME NULL;
ALTER TABLE datacapture_pagestate ADD COLUMN IF NOT EXISTS verified_data_version INT NULL;
ALTER TABLE datacapture_pagestate ADD COLUMN IF NOT EXISTS locked_data_version INT NULL;
ALTER TABLE datacapture_pagestate ADD COLUMN IF NOT EXISTS finalized_data_version INT NULL;
ALTER TABLE datacapture_pagestate ADD COLUMN IF NOT EXISTS submitted_by_id BIGINT NULL;
ALTER TABLE datacapture_pagestate ADD COLUMN IF NOT EXISTS review_started_by_id BIGINT NULL;
ALTER TABLE datacapture_pagestate ADD COLUMN IF NOT EXISTS finalized_by_id BIGINT NULL;

ALTER TABLE datacapture_pagestate ADD INDEX IF NOT EXISTS datacapture_pagestate_subject_status_idx (subject_id, status);
ALTER TABLE datacapture_pagestate ADD INDEX IF NOT EXISTS datacapture_pagestate_visit_status_idx (visit_id, status);
ALTER TABLE datacapture_pagestate ADD INDEX IF NOT EXISTS datacapture_pagestate_crf_status_idx (crf_template_id, status);

ALTER TABLE datacapture_pageentry MODIFY COLUMN status VARCHAR(32) NOT NULL;
ALTER TABLE datacapture_pageentry ADD COLUMN IF NOT EXISTS page_state_id BIGINT NULL;
ALTER TABLE datacapture_pageentry ADD COLUMN IF NOT EXISTS parent_entry_id BIGINT NULL;
ALTER TABLE datacapture_pageentry ADD COLUMN IF NOT EXISTS submitted_at DATETIME NULL;
ALTER TABLE datacapture_pageentry ADD COLUMN IF NOT EXISTS accepted_at DATETIME NULL;
ALTER TABLE datacapture_pageentry ADD COLUMN IF NOT EXISTS rejected_at DATETIME NULL;
ALTER TABLE datacapture_pageentry ADD COLUMN IF NOT EXISTS rejection_reason LONGTEXT NULL;
ALTER TABLE datacapture_pageentry ADD COLUMN IF NOT EXISTS correction_reason LONGTEXT NULL;
ALTER TABLE datacapture_pageentry ADD COLUMN IF NOT EXISTS submitted_by_id BIGINT NULL;
ALTER TABLE datacapture_pageentry ADD COLUMN IF NOT EXISTS accepted_by_id BIGINT NULL;
ALTER TABLE datacapture_pageentry ADD COLUMN IF NOT EXISTS rejected_by_id BIGINT NULL;

UPDATE datacapture_pageentry pe
JOIN datacapture_pagestate ps
  ON ps.subject_id = pe.subject_id
 AND ps.visit_id = pe.visit_id
 AND ps.crf_template_id = pe.crf_template_id
SET pe.page_state_id = ps.id
WHERE pe.page_state_id IS NULL;

ALTER TABLE datacapture_pageentry MODIFY COLUMN page_state_id BIGINT NOT NULL;
ALTER TABLE datacapture_pageentry ADD UNIQUE INDEX IF NOT EXISTS datacapture_pageentry_pagestate_version_uniq (page_state_id, entry_version);
ALTER TABLE datacapture_pageentry ADD INDEX IF NOT EXISTS datacapture_pageentry_pagestate_status_idx (page_state_id, status);

CREATE TABLE IF NOT EXISTS datacapture_fieldreview (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    page_state_id BIGINT NOT NULL,
    field_template_id BIGINT NOT NULL,
    review_type VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    data_version INT NOT NULL,
    value_snapshot LONGTEXT NULL,
    reviewed_at DATETIME NULL,
    verified_at DATETIME NULL,
    reason_code VARCHAR(64) NULL,
    reason_text LONGTEXT NULL,
    reviewed_by_id BIGINT NULL,
    verified_by_id BIGINT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    UNIQUE INDEX datacapture_fieldreview_page_field_type_uniq (page_state_id, field_template_id, review_type),
    INDEX datacapture_fieldreview_page_status_idx (page_state_id, status),
    INDEX datacapture_fieldreview_field_status_idx (field_template_id, status),
    INDEX datacapture_fieldreview_page_version_idx (page_state_id, data_version)
);

CREATE TABLE IF NOT EXISTS datacapture_pagestate_transition_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    page_state_id BIGINT NOT NULL,
    from_status VARCHAR(32) NULL,
    to_status VARCHAR(32) NOT NULL,
    data_version INT NULL,
    reason_code VARCHAR(64) NULL,
    reason_text LONGTEXT NULL,
    trigger_source VARCHAR(32) NOT NULL,
    actor_id BIGINT NULL,
    facts_json LONGTEXT NULL,
    INDEX datacapture_pagestate_trlog_page_time_idx (page_state_id, created_at),
    INDEX datacapture_pagestate_trlog_page_status_idx (page_state_id, to_status)
);

ALTER TABLE reconcile_dataquery MODIFY COLUMN status VARCHAR(32) NOT NULL;
ALTER TABLE reconcile_dataquery MODIFY COLUMN resolution_note VARCHAR(1000) NULL;
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS query_type VARCHAR(32) NOT NULL DEFAULT 'manual';
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS severity VARCHAR(16) NOT NULL DEFAULT 'minor';
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS is_blocking TINYINT NOT NULL DEFAULT 1;
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS opened_at DATETIME NULL;
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS answered_at DATETIME NULL;
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS resolved_at DATETIME NULL;
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS reason_code VARCHAR(64) NULL;
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS page_entry_id BIGINT NULL;
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS data_version INT NULL;
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS field_path VARCHAR(512) NULL;
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS value_snapshot LONGTEXT NULL;
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS opened_by_id BIGINT NULL;
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS answered_by_id BIGINT NULL;
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS resolved_by_id BIGINT NULL;
ALTER TABLE reconcile_dataquery ADD COLUMN IF NOT EXISTS closed_by_id BIGINT NULL;

UPDATE reconcile_dataquery
SET opened_at = created_at
WHERE opened_at IS NULL;

UPDATE reconcile_dataquery
SET opened_by_id = created_by_id
WHERE opened_by_id IS NULL;

ALTER TABLE reconcile_dataquery MODIFY COLUMN opened_at DATETIME NOT NULL;
ALTER TABLE reconcile_dataquery ADD INDEX IF NOT EXISTS reconcile_dataquery_page_status_idx (page_state_id, status);
ALTER TABLE reconcile_dataquery ADD INDEX IF NOT EXISTS reconcile_dataquery_page_blocking_status_idx (page_state_id, is_blocking, status);
ALTER TABLE reconcile_dataquery ADD INDEX IF NOT EXISTS reconcile_dataquery_field_status_idx (field_template_id, status);
ALTER TABLE reconcile_dataquery ADD INDEX IF NOT EXISTS reconcile_dataquery_assignee_status_idx (assigned_to_id, status);

CREATE TABLE IF NOT EXISTS crf_fieldreview_policy (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    study_id BIGINT NOT NULL,
    study_version VARCHAR(20) NOT NULL,
    crf_template_id BIGINT NOT NULL,
    field_template_id BIGINT NOT NULL,
    review_type VARCHAR(32) NOT NULL,
    is_required_for_page_verify TINYINT NOT NULL DEFAULT 0,
    is_required_for_lock TINYINT NOT NULL DEFAULT 0,
    is_blocking_if_missing TINYINT NOT NULL DEFAULT 1,
    role_required VARCHAR(64) NULL,
    is_enabled TINYINT NOT NULL DEFAULT 1,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    UNIQUE INDEX crf_fieldreview_policy_scope_uniq (
        study_id,
        study_version,
        crf_template_id,
        field_template_id,
        review_type
    ),
    INDEX crf_fieldreview_policy_crf_enabled_idx (crf_template_id, is_enabled),
    INDEX crf_fieldreview_policy_field_type_idx (field_template_id, review_type)
);
