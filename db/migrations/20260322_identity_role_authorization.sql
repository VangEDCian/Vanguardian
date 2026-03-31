-- Identity role authorization schema.
-- This migration extends django-auth based authorization with project-defined
-- roles that can aggregate both groups and permissions.

CREATE TABLE IF NOT EXISTS identity_role (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE,
    description VARCHAR(255) NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS identity_role_groups (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    role_id BIGINT NOT NULL,
    group_id INT NOT NULL,
    CONSTRAINT uq_identity_role_groups UNIQUE (role_id, group_id),
    CONSTRAINT fk_identity_role_groups_role
        FOREIGN KEY (role_id) REFERENCES identity_role (id),
    CONSTRAINT fk_identity_role_groups_group
        FOREIGN KEY (group_id) REFERENCES auth_group (id)
);

CREATE TABLE IF NOT EXISTS identity_role_permissions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    role_id BIGINT NOT NULL,
    permission_id INT NOT NULL,
    CONSTRAINT uq_identity_role_permissions UNIQUE (role_id, permission_id),
    CONSTRAINT fk_identity_role_permissions_role
        FOREIGN KEY (role_id) REFERENCES identity_role (id),
    CONSTRAINT fk_identity_role_permissions_permission
        FOREIGN KEY (permission_id) REFERENCES auth_permission (id)
);
