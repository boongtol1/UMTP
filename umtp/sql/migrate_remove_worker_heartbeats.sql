USE UMTP_RB;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_worker_heartbeats
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'worker_heartbeats';

SET @sql_drop_worker_heartbeats = IF(
  @has_worker_heartbeats = 1,
  'DROP TABLE worker_heartbeats',
  'SELECT "worker_heartbeats table missing"'
);

PREPARE stmt_drop_worker_heartbeats FROM @sql_drop_worker_heartbeats;
EXECUTE stmt_drop_worker_heartbeats;
DEALLOCATE PREPARE stmt_drop_worker_heartbeats;
