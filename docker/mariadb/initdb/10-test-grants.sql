CREATE DATABASE IF NOT EXISTS `test_vanguardian`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

GRANT ALL PRIVILEGES ON `vanguardian`.* TO 'vanguardian'@'%';
GRANT ALL PRIVILEGES ON `test_vanguardian`.* TO 'vanguardian'@'%';
GRANT CREATE, DROP, ALTER, INDEX, REFERENCES, CREATE TEMPORARY TABLES, LOCK TABLES
  ON *.* TO 'vanguardian'@'%';

FLUSH PRIVILEGES;
