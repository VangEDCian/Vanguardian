-- Identity user soft-delete schema.
-- Adds the DB-owned deleted flag used by the application reversible delete flow.

ALTER TABLE identity_user
    ADD COLUMN IF NOT EXISTS deleted TINYINT NOT NULL DEFAULT 0;
