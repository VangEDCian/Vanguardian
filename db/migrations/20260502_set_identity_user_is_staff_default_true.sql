ALTER TABLE identity_user
    MODIFY COLUMN is_staff BOOLEAN NOT NULL DEFAULT TRUE;

CREATE TABLE IF NOT EXISTS `study_eventinstance_file` (
    `id` bigint NOT NULL AUTO_INCREMENT,
    `created_at` datetime(6) NOT NULL,
    `updated_at` datetime(6) NOT NULL,
    `deleted` tinyint(1) NOT NULL DEFAULT 0,
    `study_id` bigint NOT NULL,
    `subject_id` bigint NOT NULL,
    `site_id` bigint NOT NULL,
    `event_instance_id` bigint NOT NULL,
    `original_file_name` varchar(512) NOT NULL,
    `stored_file_name` varchar(512) NOT NULL,
    `storage_relative_path` varchar(1024) NOT NULL,
    `mime_type` varchar(128) NULL,
    `file_size_bytes` bigint NOT NULL,
    `checksum_sha256` varchar(64) NULL,
    `created_by_id` bigint NULL,
    `updated_by_id` bigint NULL,
    PRIMARY KEY (`id`),
    KEY `seif_evt_del_cr_idx` (`event_instance_id`, `deleted`, `created_at`),
    KEY `seif_st_sub_del_idx` (`study_id`, `subject_id`, `deleted`),
    KEY `seif_checksum_idx` (`checksum_sha256`),
    CONSTRAINT `seif_study_fk` FOREIGN KEY (`study_id`) REFERENCES `study_study` (`id`),
    CONSTRAINT `seif_subject_fk` FOREIGN KEY (`subject_id`) REFERENCES `study_subject` (`id`),
    CONSTRAINT `seif_site_fk` FOREIGN KEY (`site_id`) REFERENCES `study_site` (`id`),
    CONSTRAINT `seif_event_instance_fk` FOREIGN KEY (`event_instance_id`) REFERENCES `study_eventinstance` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;