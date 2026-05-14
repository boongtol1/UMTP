USE UMTP_RB;

SET @schema_name = DATABASE();

SET @has_device_id = (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @schema_name
    AND table_name = 'users'
    AND column_name = 'device_id'
);
SET @add_device_id_sql = IF(
  @has_device_id > 0,
  'SELECT ''device_id column already exists''',
  'ALTER TABLE users ADD COLUMN device_id VARCHAR(200) NULL AFTER user_id'
);
PREPARE stmt FROM @add_device_id_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_device_id_index = (
  SELECT COUNT(*)
  FROM information_schema.statistics
  WHERE table_schema = @schema_name
    AND table_name = 'users'
    AND index_name = 'uq_users_device_id'
);
SET @add_device_id_index_sql = IF(
  @has_device_id_index > 0,
  'SELECT ''uq_users_device_id index already exists''',
  'ALTER TABLE users ADD UNIQUE KEY uq_users_device_id (device_id)'
);
PREPARE stmt FROM @add_device_id_index_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
