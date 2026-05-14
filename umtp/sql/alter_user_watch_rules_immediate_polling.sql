USE UMTP_RB;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_force_poll
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'user_watch_rules'
  AND COLUMN_NAME = 'force_poll';
SET @sql_force_poll = IF(
  @has_force_poll = 0,
  'ALTER TABLE user_watch_rules ADD COLUMN force_poll BOOLEAN NOT NULL DEFAULT FALSE AFTER enabled',
  'SELECT "force_poll already exists"'
);
PREPARE stmt_force_poll FROM @sql_force_poll;
EXECUTE stmt_force_poll;
DEALLOCATE PREPARE stmt_force_poll;

SELECT COUNT(*) INTO @has_last_poll_requested_at
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'user_watch_rules'
  AND COLUMN_NAME = 'last_poll_requested_at';
SET @sql_last_poll_requested_at = IF(
  @has_last_poll_requested_at = 0,
  'ALTER TABLE user_watch_rules ADD COLUMN last_poll_requested_at TIMESTAMP NULL AFTER force_poll',
  'SELECT "last_poll_requested_at already exists"'
);
PREPARE stmt_last_poll_requested_at FROM @sql_last_poll_requested_at;
EXECUTE stmt_last_poll_requested_at;
DEALLOCATE PREPARE stmt_last_poll_requested_at;
