CREATE TABLE IF NOT EXISTS governance_databaselock (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    status VARCHAR(16) NOT NULL DEFAULT 'locked',
    level VARCHAR(32) NOT NULL DEFAULT 'database',
    reason LONGTEXT NULL,
    locked_at DATETIME NOT NULL,
    unlocked_at DATETIME NULL,
    locked_by_id BIGINT NULL,
    unlocked_by_id BIGINT NULL,
    INDEX governance_databaselock_status_idx (status, level, deleted),
    INDEX governance_databaselock_locked_at_idx (locked_at)
);

CREATE TABLE IF NOT EXISTS governance_lockrecord (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    status VARCHAR(16) NOT NULL DEFAULT 'locked',
    level VARCHAR(32) NOT NULL DEFAULT 'page',
    reason LONGTEXT NULL,
    subject_id BIGINT NULL,
    visit_id BIGINT NULL,
    crf_template_id BIGINT NULL,
    page_state_id BIGINT NULL,
    locked_at DATETIME NOT NULL,
    unlocked_at DATETIME NULL,
    locked_by_id BIGINT NULL,
    unlocked_by_id BIGINT NULL,
    INDEX governance_lockrecord_scope_idx (subject_id, visit_id, crf_template_id, status, deleted),
    INDEX governance_lockrecord_page_state_idx (page_state_id, status, deleted),
    INDEX governance_lockrecord_locked_at_idx (locked_at)
);
