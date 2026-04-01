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

    CONSTRAINT fk_study_membership_user
        FOREIGN KEY (user_id)   REFERENCES identity_user (id),
    CONSTRAINT fk_study_membership_study
        FOREIGN KEY (study_id)  REFERENCES study_study (id),
    CONSTRAINT fk_study_membership_created_by
        FOREIGN KEY (created_by_id) REFERENCES identity_user (id),
    CONSTRAINT fk_study_membership_updated_by
        FOREIGN KEY (updated_by_id) REFERENCES identity_user (id),

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

    CONSTRAINT study_site_membership_user_study_site_uniq
        UNIQUE (user_id, study_id, site_id),

    CONSTRAINT fk_study_site_membership_user
        FOREIGN KEY (user_id)  REFERENCES identity_user (id),
    CONSTRAINT fk_study_site_membership_study
        FOREIGN KEY (study_id) REFERENCES study_study (id),
    CONSTRAINT fk_study_site_membership_created_by
        FOREIGN KEY (created_by_id) REFERENCES identity_user (id),
    CONSTRAINT fk_study_site_membership_updated_by
        FOREIGN KEY (updated_by_id) REFERENCES identity_user (id),

    INDEX study_site_membership_study_site_user_idx (study_id, site_id, user_id)
);
