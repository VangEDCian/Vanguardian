-- Identity user identifier hardening.
-- email and phone_number are optional, but if present they must be unique.
-- Data backfill moved to:
-- db/seeders/20260326_identity_user_unique_email_phone_number.sql

ALTER TABLE identity_user
MODIFY COLUMN email VARCHAR(254) NULL,
MODIFY COLUMN phone_number VARCHAR(32) NULL;

ALTER TABLE identity_user
ADD CONSTRAINT uq_identity_user_email UNIQUE IF NOT EXISTS (email),
ADD CONSTRAINT uq_identity_user_phone_number UNIQUE IF NOT EXISTS (phone_number);
