-- Identity user profile extension.
-- Adds display_name and phone_number so login can support phone-based
-- identification while keeping the user profile columns aligned with the
-- logical schema.

ALTER TABLE identity_user
ADD COLUMN IF NOT EXISTS display_name VARCHAR(255) NOT NULL DEFAULT '';

ALTER TABLE identity_user
ADD COLUMN IF NOT EXISTS phone_number VARCHAR(32) NULL DEFAULT NULL AFTER display_name;
