USE UMTP_RB;

SET @schema_name = DATABASE();

SET @has_enabled = (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @schema_name
    AND table_name = 'user_fair_prices'
    AND column_name = 'enabled'
);
SET @enabled_sql = IF(
  @has_enabled > 0,
  'SELECT ''enabled column already exists''',
  'ALTER TABLE user_fair_prices ADD COLUMN enabled BOOLEAN NOT NULL DEFAULT TRUE AFTER alert_drop_rate_percent'
);
PREPARE stmt FROM @enabled_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_updated_at = (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @schema_name
    AND table_name = 'user_fair_prices'
    AND column_name = 'updated_at'
);
SET @updated_at_sql = IF(
  @has_updated_at > 0,
  'SELECT ''updated_at column already exists''',
  'ALTER TABLE user_fair_prices ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at'
);
PREPARE stmt FROM @updated_at_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

UPDATE user_fair_prices
SET enabled = TRUE
WHERE enabled IS NULL;
