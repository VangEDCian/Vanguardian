CREATE TABLE IF NOT EXISTS datacapture_pagestate (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    status VARCHAR(16) NOT NULL,
    final_data LONGTEXT NOT NULL,
    verified_at DATETIME NULL,
    locked_at DATETIME NULL,
    crf_template_id BIGINT NOT NULL,
    subject_id BIGINT NOT NULL,
    visit_id BIGINT NOT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    verified_by_id BIGINT NULL,
    locked_by_id BIGINT NULL,
    UNIQUE INDEX datacapture_pagestate_subject_visit_crf_uniq (subject_id, visit_id, crf_template_id)
);

CREATE TABLE IF NOT EXISTS datacapture_pageentry (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted TINYINT NOT NULL DEFAULT 0,
    entry_no INT NOT NULL,
    entry_kind VARCHAR(16) NOT NULL,
    entry_version VARCHAR(16) NOT NULL,
    data LONGTEXT NOT NULL,
    status VARCHAR(16) NOT NULL,
    crf_template_id BIGINT NOT NULL,
    subject_id BIGINT NOT NULL,
    visit_id BIGINT NOT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    INDEX datacapture_pageentry_subject_visit_crf_version_idx (
        subject_id,
        visit_id,
        crf_template_id,
        entry_version
    )
);
