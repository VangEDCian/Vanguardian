--
-- Identity User.attempt_login for First-Login
--
ALTER TABLE `identity_user`
    ADD COLUMN IF NOT EXISTS `attempt_login` TINYINT NOT NULL DEFAULT '0';
