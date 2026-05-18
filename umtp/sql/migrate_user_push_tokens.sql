USE UMTP_RB;

CREATE TABLE IF NOT EXISTS user_push_tokens (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(100) NOT NULL,
  device_id VARCHAR(200) NULL,
  platform VARCHAR(30) NOT NULL DEFAULT 'android',
  fcm_token VARCHAR(512) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  last_error VARCHAR(255) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  last_sent_at TIMESTAMP NULL,
  UNIQUE KEY uq_user_push_tokens_fcm_token (fcm_token),
  KEY idx_user_push_tokens_user_active (user_id, is_active),
  KEY idx_user_push_tokens_device (device_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SELECT COUNT(*) INTO @has_user_push_tokens_table
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name = 'user_push_tokens';

SELECT COUNT(*) INTO @has_device_id_column
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'user_push_tokens'
  AND column_name = 'device_id';
SET @sql_add_device_id_column = IF(
  @has_user_push_tokens_table = 0,
  'SELECT ''skip user_push_tokens.device_id''',
  IF(
    @has_device_id_column = 0,
    'ALTER TABLE user_push_tokens ADD COLUMN device_id VARCHAR(200) NULL AFTER user_id',
    'SELECT ''user_push_tokens.device_id exists'''
  )
);
PREPARE stmt_add_device_id_column FROM @sql_add_device_id_column;
EXECUTE stmt_add_device_id_column;
DEALLOCATE PREPARE stmt_add_device_id_column;

SELECT COUNT(*) INTO @has_platform_column
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'user_push_tokens'
  AND column_name = 'platform';
SET @sql_add_platform_column = IF(
  @has_user_push_tokens_table = 0,
  'SELECT ''skip user_push_tokens.platform''',
  IF(
    @has_platform_column = 0,
    'ALTER TABLE user_push_tokens ADD COLUMN platform VARCHAR(30) NOT NULL DEFAULT ''android'' AFTER device_id',
    'SELECT ''user_push_tokens.platform exists'''
  )
);
PREPARE stmt_add_platform_column FROM @sql_add_platform_column;
EXECUTE stmt_add_platform_column;
DEALLOCATE PREPARE stmt_add_platform_column;

SELECT COUNT(*) INTO @has_last_error_column
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'user_push_tokens'
  AND column_name = 'last_error';
SET @sql_add_last_error_column = IF(
  @has_user_push_tokens_table = 0,
  'SELECT ''skip user_push_tokens.last_error''',
  IF(
    @has_last_error_column = 0,
    'ALTER TABLE user_push_tokens ADD COLUMN last_error VARCHAR(255) NULL AFTER is_active',
    'SELECT ''user_push_tokens.last_error exists'''
  )
);
PREPARE stmt_add_last_error_column FROM @sql_add_last_error_column;
EXECUTE stmt_add_last_error_column;
DEALLOCATE PREPARE stmt_add_last_error_column;

SELECT COUNT(*) INTO @has_last_sent_at_column
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'user_push_tokens'
  AND column_name = 'last_sent_at';
SET @sql_add_last_sent_at_column = IF(
  @has_user_push_tokens_table = 0,
  'SELECT ''skip user_push_tokens.last_sent_at''',
  IF(
    @has_last_sent_at_column = 0,
    'ALTER TABLE user_push_tokens ADD COLUMN last_sent_at TIMESTAMP NULL AFTER updated_at',
    'SELECT ''user_push_tokens.last_sent_at exists'''
  )
);
PREPARE stmt_add_last_sent_at_column FROM @sql_add_last_sent_at_column;
EXECUTE stmt_add_last_sent_at_column;
DEALLOCATE PREPARE stmt_add_last_sent_at_column;

SELECT COUNT(*) INTO @has_idx_user_active
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND table_name = 'user_push_tokens'
  AND index_name = 'idx_user_push_tokens_user_active';
SET @sql_add_idx_user_active = IF(
  @has_user_push_tokens_table = 0,
  'SELECT ''skip user_push_tokens.idx_user_push_tokens_user_active''',
  IF(
    @has_idx_user_active = 0,
    'ALTER TABLE user_push_tokens ADD INDEX idx_user_push_tokens_user_active (user_id, is_active)',
    'SELECT ''user_push_tokens.idx_user_push_tokens_user_active exists'''
  )
);
PREPARE stmt_add_idx_user_active FROM @sql_add_idx_user_active;
EXECUTE stmt_add_idx_user_active;
DEALLOCATE PREPARE stmt_add_idx_user_active;
