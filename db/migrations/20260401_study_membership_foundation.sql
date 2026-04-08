-- Study membership schema.
-- study_membership  : assigns a user into a study with exactly one in-study role.
-- study_site_membership : assigns a user into a specific site within a study.

CREATE TABLE IF NOT EXISTS study_membership (
    id              BIGINT       AUTO_INCREMENT PRIMARY KEY,
    created_at      DATETIME     NOT NULL,
    updated_at      DATETIME     NOT NULL,
    deleted         TINYINT      NOT NULL DEFAULT 0,

    user_id         BIGINT       NOT NULL,
    study_id        BIGINT       NOT NULL,
    role            VARCHAR(64)  NOT NULL,
    is_global_role  TINYINT      NOT NULL DEFAULT 0,

    created_by_id   BIGINT       NULL,
    updated_by_id   BIGINT       NULL,

    CONSTRAINT study_membership_user_study_uniq
        UNIQUE (user_id, study_id),

    INDEX study_membership_study_user_idx (study_id, user_id)
);

CREATE TABLE IF NOT EXISTS study_site_membership (
    id              BIGINT   AUTO_INCREMENT PRIMARY KEY,
    created_at      DATETIME NOT NULL,
    updated_at      DATETIME NOT NULL,
    deleted         TINYINT  NOT NULL DEFAULT 0,

    user_id         BIGINT   NOT NULL,
    study_id        BIGINT   NOT NULL,
    site_id         BIGINT   NOT NULL,

    created_by_id   BIGINT   NULL,
    updated_by_id   BIGINT   NULL,

    CONSTRAINT site_mship_usr_study_site_uq
        UNIQUE (user_id, study_id, site_id),

    INDEX site_mship_study_site_user_idx (study_id, site_id, user_id)
);
