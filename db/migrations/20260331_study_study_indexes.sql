-- Study indexes for filter and sort coverage.
-- Composite (deleted, start_date) and (deleted, end_date) cover ORDER BY
-- on top of the base queryset filter(deleted=False).
-- Composite (deleted, is_active) covers active/inactive filter.

ALTER TABLE study_study
    ADD INDEX IF NOT EXISTS study_deleted_active_idx (deleted, is_active),
    ADD INDEX IF NOT EXISTS study_deleted_start_idx (deleted, start_date),
    ADD INDEX IF NOT EXISTS study_deleted_end_idx (deleted, end_date);