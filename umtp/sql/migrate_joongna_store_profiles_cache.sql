USE UMTP_RB;

CREATE TABLE IF NOT EXISTS joongna_store_profiles (
  store_seq BIGINT PRIMARY KEY,
  store_name VARCHAR(100) NULL,
  fetch_status VARCHAR(20) NOT NULL DEFAULT 'success',
  error_message TEXT NULL,
  last_fetched_at TIMESTAMP NULL,
  next_retry_at TIMESTAMP NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_joongna_store_profiles_retry (next_retry_at),
  KEY idx_joongna_store_profiles_status (fetch_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_store_name
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_store_profiles'
  AND COLUMN_NAME = 'store_name';
SET @sql_store_name = IF(
  @has_store_name = 0,
  'ALTER TABLE joongna_store_profiles ADD COLUMN store_name VARCHAR(100) NULL AFTER store_seq',
  'SELECT "joongna_store_profiles.store_name exists"'
);
PREPARE stmt_store_name FROM @sql_store_name;
EXECUTE stmt_store_name;
DEALLOCATE PREPARE stmt_store_name;

SELECT COUNT(*) INTO @has_fetch_status
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_store_profiles'
  AND COLUMN_NAME = 'fetch_status';
SET @sql_fetch_status = IF(
  @has_fetch_status = 0,
  'ALTER TABLE joongna_store_profiles ADD COLUMN fetch_status VARCHAR(20) NOT NULL DEFAULT ''success'' AFTER store_name',
  'SELECT "joongna_store_profiles.fetch_status exists"'
);
PREPARE stmt_fetch_status FROM @sql_fetch_status;
EXECUTE stmt_fetch_status;
DEALLOCATE PREPARE stmt_fetch_status;

SELECT COUNT(*) INTO @has_error_message
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_store_profiles'
  AND COLUMN_NAME = 'error_message';
SET @sql_error_message = IF(
  @has_error_message = 0,
  'ALTER TABLE joongna_store_profiles ADD COLUMN error_message TEXT NULL AFTER fetch_status',
  'SELECT "joongna_store_profiles.error_message exists"'
);
PREPARE stmt_error_message FROM @sql_error_message;
EXECUTE stmt_error_message;
DEALLOCATE PREPARE stmt_error_message;

SELECT COUNT(*) INTO @has_last_fetched_at
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_store_profiles'
  AND COLUMN_NAME = 'last_fetched_at';
SET @sql_last_fetched_at = IF(
  @has_last_fetched_at = 0,
  'ALTER TABLE joongna_store_profiles ADD COLUMN last_fetched_at TIMESTAMP NULL AFTER error_message',
  'SELECT "joongna_store_profiles.last_fetched_at exists"'
);
PREPARE stmt_last_fetched_at FROM @sql_last_fetched_at;
EXECUTE stmt_last_fetched_at;
DEALLOCATE PREPARE stmt_last_fetched_at;

SELECT COUNT(*) INTO @has_next_retry_at
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_store_profiles'
  AND COLUMN_NAME = 'next_retry_at';
SET @sql_next_retry_at = IF(
  @has_next_retry_at = 0,
  'ALTER TABLE joongna_store_profiles ADD COLUMN next_retry_at TIMESTAMP NULL AFTER last_fetched_at',
  'SELECT "joongna_store_profiles.next_retry_at exists"'
);
PREPARE stmt_next_retry_at FROM @sql_next_retry_at;
EXECUTE stmt_next_retry_at;
DEALLOCATE PREPARE stmt_next_retry_at;

SELECT COUNT(*) INTO @has_created_at
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_store_profiles'
  AND COLUMN_NAME = 'created_at';
SET @sql_created_at = IF(
  @has_created_at = 0,
  'ALTER TABLE joongna_store_profiles ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP AFTER next_retry_at',
  'SELECT "joongna_store_profiles.created_at exists"'
);
PREPARE stmt_created_at FROM @sql_created_at;
EXECUTE stmt_created_at;
DEALLOCATE PREPARE stmt_created_at;

SELECT COUNT(*) INTO @has_updated_at
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_store_profiles'
  AND COLUMN_NAME = 'updated_at';
SET @sql_updated_at = IF(
  @has_updated_at = 0,
  'ALTER TABLE joongna_store_profiles ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at',
  'SELECT "joongna_store_profiles.updated_at exists"'
);
PREPARE stmt_updated_at FROM @sql_updated_at;
EXECUTE stmt_updated_at;
DEALLOCATE PREPARE stmt_updated_at;

SELECT COUNT(*) INTO @has_idx_retry
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_store_profiles'
  AND INDEX_NAME = 'idx_joongna_store_profiles_retry';
SET @sql_idx_retry = IF(
  @has_idx_retry = 0,
  'ALTER TABLE joongna_store_profiles ADD INDEX idx_joongna_store_profiles_retry (next_retry_at)',
  'SELECT "idx_joongna_store_profiles_retry exists"'
);
PREPARE stmt_idx_retry FROM @sql_idx_retry;
EXECUTE stmt_idx_retry;
DEALLOCATE PREPARE stmt_idx_retry;

SELECT COUNT(*) INTO @has_idx_status
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_store_profiles'
  AND INDEX_NAME = 'idx_joongna_store_profiles_status';
SET @sql_idx_status = IF(
  @has_idx_status = 0,
  'ALTER TABLE joongna_store_profiles ADD INDEX idx_joongna_store_profiles_status (fetch_status)',
  'SELECT "idx_joongna_store_profiles_status exists"'
);
PREPARE stmt_idx_status FROM @sql_idx_status;
EXECUTE stmt_idx_status;
DEALLOCATE PREPARE stmt_idx_status;
