USE UMTP_RB;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_is_read
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'is_read';
SET @sql_is_read = IF(
  @has_is_read = 0,
  'ALTER TABLE alert_events ADD COLUMN is_read TINYINT(1) NOT NULL DEFAULT 0 AFTER error_message',
  'SELECT "is_read exists"'
);
PREPARE stmt_is_read FROM @sql_is_read;
EXECUTE stmt_is_read;
DEALLOCATE PREPARE stmt_is_read;

SELECT COUNT(*) INTO @has_read_at
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'read_at';
SET @sql_read_at = IF(
  @has_read_at = 0,
  'ALTER TABLE alert_events ADD COLUMN read_at DATETIME NULL AFTER is_read',
  'SELECT "read_at exists"'
);
PREPARE stmt_read_at FROM @sql_read_at;
EXECUTE stmt_read_at;
DEALLOCATE PREPARE stmt_read_at;

SELECT COUNT(*) INTO @has_idx_user_read
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND INDEX_NAME = 'idx_alert_events_user_is_read';
SET @sql_idx_user_read = IF(
  @has_idx_user_read = 0,
  'ALTER TABLE alert_events ADD INDEX idx_alert_events_user_is_read (user_id, is_read, read_at)',
  'SELECT "idx_alert_events_user_is_read exists"'
);
PREPARE stmt_idx_user_read FROM @sql_idx_user_read;
EXECUTE stmt_idx_user_read;
DEALLOCATE PREPARE stmt_idx_user_read;
