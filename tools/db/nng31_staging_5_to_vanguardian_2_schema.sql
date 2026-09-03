-- Align the schema from `nng31_staging (5).sql` with `vanguardian (2).sql`.
--
-- Compared dumps:
-- - C:/Users/trungthudo13/Downloads/nng31_staging (5).sql
-- - C:/Users/trungthudo13/Downloads/vanguardian (2).sql
--
-- MariaDB DDL auto-commits. Take a database backup before running this file.
-- Run with the target database selected, for example:
--   mariadb -u... -p... nng31_staging < tools/db/nng31_staging_5_to_vanguardian_2_schema.sql
--
-- The migration is data-preserving and re-runnable. Existing business rows are
-- not deleted; new policy fields receive legacy-compatible values, and blank
-- randomization formatting fields are inferred from existing slot codes.

-- Randomization code formatting and automatic event-transition execution.
ALTER TABLE `study_randomization_scheme`
  ADD COLUMN IF NOT EXISTS `randomization_code_prefix` varchar(32) NOT NULL DEFAULT ''
    AFTER `target_randomized_total`,
  ADD COLUMN IF NOT EXISTS `randomization_code_padding` smallint(5) unsigned NOT NULL DEFAULT 3
    CHECK (`randomization_code_padding` >= 0) AFTER `randomization_code_prefix`;

UPDATE `study_randomization_scheme` AS scheme
JOIN (
  SELECT
    scheme_id,
    SUBSTRING(
      MIN(randomization_code),
      1,
      LENGTH(MIN(randomization_code)) - LOCATE('-', REVERSE(MIN(randomization_code)))
    ) AS inferred_prefix,
    LOCATE('-', REVERSE(MIN(randomization_code))) - 1 AS inferred_padding
  FROM `study_randomization_slot`
  WHERE deleted = 0
    AND randomization_code IS NOT NULL
    AND randomization_code REGEXP '^.+-[0-9]+$'
  GROUP BY scheme_id
) AS existing_format ON existing_format.scheme_id = scheme.id
SET
  scheme.randomization_code_prefix = existing_format.inferred_prefix,
  scheme.randomization_code_padding = existing_format.inferred_padding
WHERE scheme.randomization_code_prefix = ''
  AND existing_format.inferred_padding BETWEEN 1 AND 12;

ALTER TABLE `study_randomization_scheme`
  MODIFY COLUMN `randomization_code_prefix` varchar(32) NOT NULL
    AFTER `target_randomized_total`,
  MODIFY COLUMN `randomization_code_padding` smallint(5) unsigned NOT NULL
    CHECK (`randomization_code_padding` >= 0) AFTER `randomization_code_prefix`,
  MODIFY COLUMN `eligibility_rule_code` varchar(64) DEFAULT NULL
    AFTER `randomization_code_padding`,
  MODIFY COLUMN `requires_screening_pass` tinyint(1) NOT NULL
    AFTER `eligibility_rule_code`,
  MODIFY COLUMN `is_open_label` tinyint(1) NOT NULL
    AFTER `requires_screening_pass`,
  MODIFY COLUMN `status` varchar(32) NOT NULL AFTER `is_open_label`,
  MODIFY COLUMN `effective_from` datetime(6) DEFAULT NULL AFTER `status`,
  MODIFY COLUMN `effective_to` datetime(6) DEFAULT NULL AFTER `effective_from`,
  MODIFY COLUMN `created_by_id` bigint(20) DEFAULT NULL AFTER `effective_to`,
  MODIFY COLUMN `approved_by_id` bigint(20) DEFAULT NULL AFTER `created_by_id`,
  MODIFY COLUMN `master_list_version` varchar(64) DEFAULT NULL AFTER `approved_by_id`,
  MODIFY COLUMN `master_list_checksum` varchar(64) DEFAULT NULL AFTER `master_list_version`,
  MODIFY COLUMN `master_list_source_filename` varchar(255) DEFAULT NULL
    AFTER `master_list_checksum`,
  MODIFY COLUMN `master_list_imported_by_id` bigint(20) DEFAULT NULL
    AFTER `master_list_source_filename`,
  MODIFY COLUMN `master_list_imported_at` datetime(6) DEFAULT NULL
    AFTER `master_list_imported_by_id`,
  MODIFY COLUMN `master_list_approved_by_id` bigint(20) DEFAULT NULL
    AFTER `master_list_imported_at`,
  MODIFY COLUMN `master_list_approved_at` datetime(6) DEFAULT NULL
    AFTER `master_list_approved_by_id`,
  MODIFY COLUMN `master_list_locked_at` datetime(6) DEFAULT NULL
    AFTER `master_list_approved_at`,
  MODIFY COLUMN `notes` longtext DEFAULT NULL AFTER `master_list_locked_at`,
  MODIFY COLUMN `study_id` bigint(20) NOT NULL AFTER `notes`;

ALTER TABLE `study_randomization_slot`
  MODIFY COLUMN `randomization_code` varchar(64) DEFAULT NULL AFTER `sequence_no`;

ALTER TABLE `study_subject_period`
  MODIFY COLUMN `kit_code` varchar(64) DEFAULT NULL AFTER `treatment_code`;

ALTER TABLE `study_event_transition_rule`
  ADD COLUMN IF NOT EXISTS `auto_execute` tinyint(1) NOT NULL DEFAULT 0 AFTER `auto_create`,
  MODIFY COLUMN `auto_execute` tinyint(1) NOT NULL AFTER `auto_create`;

-- Subject identifier policy. The temporary defaults populate existing Study
-- rows; the following MODIFY clauses remove DB defaults to match the target.
ALTER TABLE `study_study`
  ADD COLUMN IF NOT EXISTS `lock_subject_code_after_assignment` tinyint(1) NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS `screening_code_pattern` varchar(128) NOT NULL
    DEFAULT '{study_code}-S{sequence:03d}',
  ADD COLUMN IF NOT EXISTS `screening_identifier_mode` varchar(16) NOT NULL DEFAULT 'generated',
  ADD COLUMN IF NOT EXISTS `subject_code_pattern` varchar(128) NOT NULL
    DEFAULT '{study_code}-{sequence:03d}',
  ADD COLUMN IF NOT EXISTS `subject_code_uniqueness_scope` varchar(16) NOT NULL DEFAULT 'study_site',
  ADD COLUMN IF NOT EXISTS `subject_identifier_mode` varchar(48) NOT NULL
    DEFAULT 'generated_at_enrollment',
  ADD COLUMN IF NOT EXISTS `crf_page_lifecycle_configured` tinyint(1) NOT NULL DEFAULT 0;

ALTER TABLE `study_study`
  MODIFY COLUMN `lock_subject_code_after_assignment` tinyint(1) NOT NULL AFTER `updated_by_id`,
  MODIFY COLUMN `screening_code_pattern` varchar(128) NOT NULL
    AFTER `lock_subject_code_after_assignment`,
  MODIFY COLUMN `screening_identifier_mode` varchar(16) NOT NULL
    AFTER `screening_code_pattern`,
  MODIFY COLUMN `subject_code_pattern` varchar(128) NOT NULL
    AFTER `screening_identifier_mode`,
  MODIFY COLUMN `subject_code_uniqueness_scope` varchar(16) NOT NULL
    AFTER `subject_code_pattern`,
  MODIFY COLUMN `subject_identifier_mode` varchar(48) NOT NULL
    AFTER `subject_code_uniqueness_scope`,
  MODIFY COLUMN `crf_page_lifecycle_configured` tinyint(1) NOT NULL
    AFTER `subject_identifier_mode`;

CREATE TABLE IF NOT EXISTS `study_subject_identifier_history` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `identifier_type` varchar(32) NOT NULL,
  `from_value` varchar(64) DEFAULT NULL,
  `to_value` varchar(64) DEFAULT NULL,
  `assignment_source` varchar(48) NOT NULL,
  `occurred_at` datetime(6) NOT NULL,
  `actor_user_id` bigint(20) DEFAULT NULL,
  `subject_id` bigint(20) NOT NULL,
  `related_randomization_event_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `subj_ident_hist_time_idx` (`subject_id`, `occurred_at`),
  KEY `subj_ident_hist_value_idx` (`identifier_type`, `to_value`),
  KEY `study_subject_identi_related_randomizatio_313fbcfc_fk_study_ran`
    (`related_randomization_event_id`),
  CONSTRAINT `study_subject_identi_related_randomizatio_313fbcfc_fk_study_ran`
    FOREIGN KEY (`related_randomization_event_id`) REFERENCES `study_randomization_event` (`id`),
  CONSTRAINT `study_subject_identi_subject_id_df609d87_fk_study_sub`
    FOREIGN KEY (`subject_id`) REFERENCES `study_subject` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `study_subject_identifier_migration_batch` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `operation_type` varchar(16) NOT NULL,
  `from_policy_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL
    CHECK (json_valid(`from_policy_json`)),
  `to_policy_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL
    CHECK (json_valid(`to_policy_json`)),
  `plan_hash` varchar(64) NOT NULL,
  `occurred_at` datetime(6) NOT NULL,
  `actor_user_id` bigint(20) DEFAULT NULL,
  `reverses_batch_id` bigint(20) DEFAULT NULL,
  `study_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `reverses_batch_id` (`reverses_batch_id`),
  KEY `subj_ident_mig_st_time_idx` (`study_id`, `occurred_at`),
  CONSTRAINT `study_subject_identi_reverses_batch_id_37d41d9a_fk_study_sub`
    FOREIGN KEY (`reverses_batch_id`) REFERENCES `study_subject_identifier_migration_batch` (`id`),
  CONSTRAINT `study_subject_identi_study_id_65128349_fk_study_stu`
    FOREIGN KEY (`study_id`) REFERENCES `study_study` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `study_subject_identifier_migration_item` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `from_subject_code` varchar(64) DEFAULT NULL,
  `to_subject_code` varchar(64) DEFAULT NULL,
  `migration_batch_id` bigint(20) NOT NULL,
  `subject_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `subj_ident_mig_item_batch_subj_uq` (`migration_batch_id`, `subject_id`),
  KEY `study_subject_identi_subject_id_3abdb799_fk_study_sub` (`subject_id`),
  CONSTRAINT `study_subject_identi_migration_batch_id_7dc7e94e_fk_study_sub`
    FOREIGN KEY (`migration_batch_id`) REFERENCES `study_subject_identifier_migration_batch` (`id`),
  CONSTRAINT `study_subject_identi_subject_id_3abdb799_fk_study_sub`
    FOREIGN KEY (`subject_id`) REFERENCES `study_subject` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `study_subject_identifier_migration_period_item` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `from_kit_code` varchar(64) DEFAULT NULL,
  `to_kit_code` varchar(64) DEFAULT NULL,
  `migration_item_id` bigint(20) NOT NULL,
  `period_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `subj_ident_mig_period_item_uq` (`migration_item_id`, `period_id`),
  KEY `study_subject_identi_period_id_fecc4679_fk_study_sub` (`period_id`),
  CONSTRAINT `study_subject_identi_migration_item_id_1961ca91_fk_study_sub`
    FOREIGN KEY (`migration_item_id`) REFERENCES `study_subject_identifier_migration_item` (`id`),
  CONSTRAINT `study_subject_identi_period_id_fecc4679_fk_study_sub`
    FOREIGN KEY (`period_id`) REFERENCES `study_subject_period` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- CRF Page lifecycle and page-level certification evidence.
CREATE TABLE IF NOT EXISTS `study_crf_page_lifecycle_step` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `step_code` varchar(16) NOT NULL,
  `display_order` smallint(5) unsigned NOT NULL CHECK (`display_order` >= 0),
  `allowed_role_ids` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL
    CHECK (json_valid(`allowed_role_ids`)),
  `created_by_id` bigint(20) DEFAULT NULL,
  `updated_by_id` bigint(20) DEFAULT NULL,
  `study_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `study_crf_page_lifecycle_step_uniq` (`study_id`, `step_code`),
  UNIQUE KEY `study_crf_page_lifecycle_order_uniq` (`study_id`, `display_order`),
  KEY `study_crf_pg_lc_order_idx` (`study_id`, `display_order`),
  CONSTRAINT `study_crf_page_lifec_study_id_cce4a289_fk_study_stu`
    FOREIGN KEY (`study_id`) REFERENCES `study_study` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE `datacapture_pagestate`
  ADD COLUMN IF NOT EXISTS `certified_at` datetime(6) DEFAULT NULL AFTER `visit_id`,
  ADD COLUMN IF NOT EXISTS `certified_by_id` bigint(20) DEFAULT NULL AFTER `certified_at`,
  ADD COLUMN IF NOT EXISTS `certified_data_version` int(11) DEFAULT NULL AFTER `certified_by_id`,
  MODIFY COLUMN `repeat_index` int(11) NOT NULL AFTER `finalized_data_version`,
  MODIFY COLUMN `instance_key` varchar(64) DEFAULT NULL AFTER `repeat_index`,
  MODIFY COLUMN `created_by_id` bigint(20) DEFAULT NULL AFTER `instance_key`,
  MODIFY COLUMN `updated_by_id` bigint(20) DEFAULT NULL AFTER `created_by_id`,
  MODIFY COLUMN `submitted_by_id` bigint(20) DEFAULT NULL AFTER `updated_by_id`,
  MODIFY COLUMN `review_started_by_id` bigint(20) DEFAULT NULL AFTER `submitted_by_id`,
  MODIFY COLUMN `verified_by_id` bigint(20) DEFAULT NULL AFTER `review_started_by_id`,
  MODIFY COLUMN `locked_by_id` bigint(20) DEFAULT NULL AFTER `verified_by_id`,
  MODIFY COLUMN `finalized_by_id` bigint(20) DEFAULT NULL AFTER `locked_by_id`,
  MODIFY COLUMN `crf_template_id` bigint(20) NOT NULL AFTER `finalized_by_id`,
  MODIFY COLUMN `current_entry_id` bigint(20) DEFAULT NULL AFTER `crf_template_id`,
  MODIFY COLUMN `event_form_binding_id` bigint(20) DEFAULT NULL AFTER `current_entry_id`,
  MODIFY COLUMN `subject_id` bigint(20) NOT NULL AFTER `event_form_binding_id`,
  MODIFY COLUMN `visit_id` bigint(20) NOT NULL AFTER `subject_id`,
  MODIFY COLUMN `certified_at` datetime(6) DEFAULT NULL AFTER `visit_id`,
  MODIFY COLUMN `certified_by_id` bigint(20) DEFAULT NULL AFTER `certified_at`,
  MODIFY COLUMN `certified_data_version` int(11) DEFAULT NULL AFTER `certified_by_id`;

-- Normalize older column ordering/defaults that differ from the current
-- vanguardian schema but do not require data conversion.
ALTER TABLE `study_eventattestation_policy`
  MODIFY COLUMN `invalidate_on_query_change` tinyint(1) NOT NULL
    AFTER `invalidate_on_scope_change`;

ALTER TABLE `study_eventdefinition`
  MODIFY COLUMN `lifecycle_role` varchar(32) NOT NULL AFTER `event_category`;

ALTER TABLE `study_subject`
  MODIFY COLUMN `enrollment_current_sequence` bigint(20) DEFAULT NULL
    AFTER `current_sequence`,
  MODIFY COLUMN `lifecycle_status` varchar(40) NOT NULL
    AFTER `enrollment_current_sequence`,
  MODIFY COLUMN `lifecycle_status_at` datetime(6) DEFAULT NULL
    AFTER `lifecycle_status`,
  MODIFY COLUMN `lifecycle_reason_code` varchar(64) DEFAULT NULL
    AFTER `lifecycle_status_at`,
  MODIFY COLUMN `lifecycle_reason_text` longtext DEFAULT NULL
    AFTER `lifecycle_reason_code`;

-- Normalize legacy reconcile FK/index names and snapshot column order.
ALTER TABLE `reconcile_validation_issue_snapshot`
  DROP FOREIGN KEY IF EXISTS `reconcile_vi_snap_run_fk`,
  DROP FOREIGN KEY IF EXISTS `reconcile_validation_validation_run_id_fce4541f_fk_reconcile`;

ALTER TABLE `reconcile_validation_issue_snapshot`
  MODIFY COLUMN `result` varchar(16) NOT NULL AFTER `created_at`,
  MODIFY COLUMN `evaluated_values_json`
    longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL
    CHECK (json_valid(`evaluated_values_json`)) AFTER `result`,
  MODIFY COLUMN `message` longtext NOT NULL AFTER `evaluated_values_json`,
  MODIFY COLUMN `severity` varchar(30) NOT NULL AFTER `message`,
  MODIFY COLUMN `data_version` bigint(20) NOT NULL AFTER `severity`,
  MODIFY COLUMN `related_audit_event_id` bigint(20) DEFAULT NULL AFTER `data_version`,
  MODIFY COLUMN `validation_issue_id` bigint(20) NOT NULL AFTER `related_audit_event_id`,
  MODIFY COLUMN `validation_run_id` bigint(20) NOT NULL AFTER `validation_issue_id`,
  ADD CONSTRAINT `reconcile_validation_validation_run_id_fce4541f_fk_reconcile`
    FOREIGN KEY (`validation_run_id`) REFERENCES `reconcile_validation_run` (`id`);

ALTER TABLE `reconcile_validation_run`
  DROP FOREIGN KEY IF EXISTS `reconcile_vi_run_audit_fk`,
  DROP FOREIGN KEY IF EXISTS `reconcile_vi_run_form_fk`,
  DROP FOREIGN KEY IF EXISTS `reconcile_validation_related_audit_event__07af1c84_fk_audit_aud`,
  DROP FOREIGN KEY IF EXISTS `reconcile_validation_form_instance_id_615aff5d_fk_datacaptu`;

ALTER TABLE `reconcile_validation_run`
  DROP INDEX IF EXISTS `reconcile_vi_run_audit_fk`,
  ADD INDEX IF NOT EXISTS `reconcile_validation_related_audit_event__07af1c84_fk_audit_aud`
    (`related_audit_event_id`),
  ADD CONSTRAINT `reconcile_validation_form_instance_id_615aff5d_fk_datacaptu`
    FOREIGN KEY (`form_instance_id`) REFERENCES `datacapture_pagestate` (`id`),
  ADD CONSTRAINT `reconcile_validation_related_audit_event__07af1c84_fk_audit_aud`
    FOREIGN KEY (`related_audit_event_id`) REFERENCES `audit_auditevent` (`id`);

-- Record the migration nodes represented by this schema alignment. These
-- inserts are conditional so the file is safe when a node was already marked.
INSERT INTO `django_migrations` (`app`, `name`, `applied`)
SELECT 'study', '0002_study_lock_subject_code_after_assignment_and_more', UTC_TIMESTAMP(6)
WHERE NOT EXISTS (
  SELECT 1 FROM `django_migrations`
  WHERE `app` = 'study' AND `name` = '0002_study_lock_subject_code_after_assignment_and_more'
);

INSERT INTO `django_migrations` (`app`, `name`, `applied`)
SELECT 'subject', '0002_subjectidentifierhistory', UTC_TIMESTAMP(6)
WHERE NOT EXISTS (
  SELECT 1 FROM `django_migrations`
  WHERE `app` = 'subject' AND `name` = '0002_subjectidentifierhistory'
);

INSERT INTO `django_migrations` (`app`, `name`, `applied`)
SELECT 'subject', '0003_alter_subjectidentifierhistory_assignment_source', UTC_TIMESTAMP(6)
WHERE NOT EXISTS (
  SELECT 1 FROM `django_migrations`
  WHERE `app` = 'subject'
    AND `name` = '0003_alter_subjectidentifierhistory_assignment_source'
);

INSERT INTO `django_migrations` (`app`, `name`, `applied`)
SELECT 'subject', '0004_remove_subjectidentifierhistory_related_event_id_and_more', UTC_TIMESTAMP(6)
WHERE NOT EXISTS (
  SELECT 1 FROM `django_migrations`
  WHERE `app` = 'subject'
    AND `name` = '0004_remove_subjectidentifierhistory_related_event_id_and_more'
);

INSERT INTO `django_migrations` (`app`, `name`, `applied`)
SELECT 'subject', '0005_alter_subjectidentifierhistory_to_value_and_more', UTC_TIMESTAMP(6)
WHERE NOT EXISTS (
  SELECT 1 FROM `django_migrations`
  WHERE `app` = 'subject'
    AND `name` = '0005_alter_subjectidentifierhistory_to_value_and_more'
);

INSERT INTO `django_migrations` (`app`, `name`, `applied`)
SELECT 'datacapture', '0002_datacapturepagestate_certified_at_and_more', UTC_TIMESTAMP(6)
WHERE NOT EXISTS (
  SELECT 1 FROM `django_migrations`
  WHERE `app` = 'datacapture'
    AND `name` = '0002_datacapturepagestate_certified_at_and_more'
);

INSERT INTO `django_migrations` (`app`, `name`, `applied`)
SELECT 'study', '0003_studycrfpagelifecyclestep', UTC_TIMESTAMP(6)
WHERE NOT EXISTS (
  SELECT 1 FROM `django_migrations`
  WHERE `app` = 'study' AND `name` = '0003_studycrfpagelifecyclestep'
);

INSERT INTO `django_migrations` (`app`, `name`, `applied`)
SELECT 'study', '0004_study_crf_page_lifecycle_configured', UTC_TIMESTAMP(6)
WHERE NOT EXISTS (
  SELECT 1 FROM `django_migrations`
  WHERE `app` = 'study' AND `name` = '0004_study_crf_page_lifecycle_configured'
);
