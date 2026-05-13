-- final_data is reserved for post-submit verification metadata (e.g. __form_verification__);
-- capture payloads live on datacapture_pageentry.data. New rows start with NULL until verified.
ALTER TABLE datacapture_pagestate MODIFY COLUMN final_data LONGTEXT NULL;
