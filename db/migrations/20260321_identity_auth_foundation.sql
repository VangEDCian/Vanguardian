-- Identity foundation schema.
-- This migration assumes Django core tables such as django_content_type,
-- auth_group, and auth_permission are already available.
-- Permission records are created by Django migrate via
-- django_content_type + Meta.permissions.

CREATE TABLE IF NOT EXISTS identity_user (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    password VARCHAR(128) NOT NULL,
    last_login DATETIME NULL,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    username VARCHAR(150) NOT NULL UNIQUE,
    first_name VARCHAR(150) NOT NULL DEFAULT '',
    last_name VARCHAR(150) NOT NULL DEFAULT '',
    email VARCHAR(254) NOT NULL DEFAULT '',
    is_staff BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    date_joined DATETIME NOT NULL,
    INDEX idx_identity_user_username (username)
);

CREATE TABLE IF NOT EXISTS identity_user_groups (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    group_id INT NOT NULL,
    CONSTRAINT uq_identity_user_groups UNIQUE (user_id, group_id),
    CONSTRAINT fk_identity_user_groups_user
        FOREIGN KEY (user_id) REFERENCES identity_user (id),
    CONSTRAINT fk_identity_user_groups_group
        FOREIGN KEY (group_id) REFERENCES auth_group (id)
);

CREATE TABLE IF NOT EXISTS identity_user_user_permissions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    permission_id INT NOT NULL,
    CONSTRAINT uq_identity_user_user_permissions UNIQUE (user_id, permission_id),
    CONSTRAINT fk_identity_user_user_permissions_user
        FOREIGN KEY (user_id) REFERENCES identity_user (id),
    CONSTRAINT fk_identity_user_user_permissions_permission
        FOREIGN KEY (permission_id) REFERENCES auth_permission (id)
);
