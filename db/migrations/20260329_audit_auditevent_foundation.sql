-- Audit foundation schema.
-- This migration assumes identity_user already exists.

CREATE TABLE IF NOT EXISTS audit_auditevent (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    action VARCHAR(64) NOT NULL,
    object_type VARCHAR(64) NOT NULL,
    object_id VARCHAR(64) NOT NULL,
    before_data LONGTEXT NOT NULL,
    after_data LONGTEXT NOT NULL,
    ip_address CHAR(39) NULL,
    user_agent VARCHAR(255) NOT NULL,
    user_id BIGINT NULL,
    created_by_id BIGINT NULL,
    updated_by_id BIGINT NULL,
    INDEX audit_auditevent_obj_time_idx (object_type, object_id, created_at),
    CONSTRAINT fk_audit_auditevent_user
        FOREIGN KEY (user_id) REFERENCES identity_user (id),
    CONSTRAINT fk_audit_auditevent_created_by
        FOREIGN KEY (created_by_id) REFERENCES identity_user (id),
    CONSTRAINT fk_audit_auditevent_updated_by
        FOREIGN KEY (updated_by_id) REFERENCES identity_user (id)
);
