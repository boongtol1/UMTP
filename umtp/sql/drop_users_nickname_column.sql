USE UMTP_RB;

SET @schema_name = DATABASE();
SET @has_nickname = (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @schema_name
    AND table_name = 'users'
    AND column_name = 'nickname'
);
SET @drop_nickname_sql = IF(
  @has_nickname > 0,
  'ALTER TABLE users DROP COLUMN nickname',
  'SELECT ''nickname column already removed'''
);
PREPARE stmt FROM @drop_nickname_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
