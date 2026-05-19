USE UMTP_RB;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_is_read_archive_cleared
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'is_read_archive_cleared';
SET @sql_is_read_archive_cleared = IF(
  @has_is_read_archive_cleared = 0,
  'ALTER TABLE alert_events ADD COLUMN is_read_archive_cleared TINYINT(1) NOT NULL DEFAULT 0 AFTER read_at',
  'SELECT "is_read_archive_cleared exists"'
);
PREPARE stmt_is_read_archive_cleared FROM @sql_is_read_archive_cleared;
EXECUTE stmt_is_read_archive_cleared;
DEALLOCATE PREPARE stmt_is_read_archive_cleared;

SELECT COUNT(*) INTO @has_read_archive_cleared_at
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'read_archive_cleared_at';
SET @sql_read_archive_cleared_at = IF(
  @has_read_archive_cleared_at = 0,
  'ALTER TABLE alert_events ADD COLUMN read_archive_cleared_at DATETIME NULL AFTER is_read_archive_cleared',
  'SELECT "read_archive_cleared_at exists"'
);
PREPARE stmt_read_archive_cleared_at FROM @sql_read_archive_cleared_at;
EXECUTE stmt_read_archive_cleared_at;
DEALLOCATE PREPARE stmt_read_archive_cleared_at;

SELECT COUNT(*) INTO @has_idx_user_read_archive_clear
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND INDEX_NAME = 'idx_alert_events_user_read_archive_clear';
SET @sql_idx_user_read_archive_clear = IF(
  @has_idx_user_read_archive_clear = 0,
  'ALTER TABLE alert_events ADD INDEX idx_alert_events_user_read_archive_clear (user_id, is_read, is_read_archive_cleared, read_archive_cleared_at)',
  'SELECT "idx_alert_events_user_read_archive_clear exists"'
);
PREPARE stmt_idx_user_read_archive_clear FROM @sql_idx_user_read_archive_clear;
EXECUTE stmt_idx_user_read_archive_clear;
DEALLOCATE PREPARE stmt_idx_user_read_archive_clear;
