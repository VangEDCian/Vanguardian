CREATE TABLE IF NOT EXISTS identity_user_roles (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    INDEX idx_identity_user_roles_user (user_id),
    INDEX idx_identity_user_roles_role (role_id),
    UNIQUE INDEX idx_identity_user_roles_user_role (user_id, role_id)
);
