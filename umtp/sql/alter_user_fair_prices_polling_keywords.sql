USE UMTP_RB;

SET @schema_name = DATABASE();

SET @has_search_keyword = (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @schema_name
    AND table_name = 'user_fair_prices'
    AND column_name = 'search_keyword'
);
SET @search_keyword_sql = IF(
  @has_search_keyword > 0,
  'SELECT ''search_keyword already exists''',
  'ALTER TABLE user_fair_prices ADD COLUMN search_keyword VARCHAR(255) NULL AFTER enabled'
);
PREPARE stmt FROM @search_keyword_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_poll_interval_seconds = (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @schema_name
    AND table_name = 'user_fair_prices'
    AND column_name = 'poll_interval_seconds'
);
SET @poll_interval_seconds_sql = IF(
  @has_poll_interval_seconds > 0,
  'SELECT ''poll_interval_seconds already exists''',
  'ALTER TABLE user_fair_prices ADD COLUMN poll_interval_seconds INT NOT NULL DEFAULT 60 AFTER search_keyword'
);
PREPARE stmt FROM @poll_interval_seconds_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_force_poll = (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @schema_name
    AND table_name = 'user_fair_prices'
    AND column_name = 'force_poll'
);
SET @force_poll_sql = IF(
  @has_force_poll > 0,
  'SELECT ''force_poll already exists''',
  'ALTER TABLE user_fair_prices ADD COLUMN force_poll BOOLEAN NOT NULL DEFAULT FALSE AFTER poll_interval_seconds'
);
PREPARE stmt FROM @force_poll_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_last_poll_requested_at = (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @schema_name
    AND table_name = 'user_fair_prices'
    AND column_name = 'last_poll_requested_at'
);
SET @last_poll_requested_at_sql = IF(
  @has_last_poll_requested_at > 0,
  'SELECT ''last_poll_requested_at already exists''',
  'ALTER TABLE user_fair_prices ADD COLUMN last_poll_requested_at TIMESTAMP NULL AFTER force_poll'
);
PREPARE stmt FROM @last_poll_requested_at_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_last_polled_at = (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @schema_name
    AND table_name = 'user_fair_prices'
    AND column_name = 'last_polled_at'
);
SET @last_polled_at_sql = IF(
  @has_last_polled_at > 0,
  'SELECT ''last_polled_at already exists''',
  'ALTER TABLE user_fair_prices ADD COLUMN last_polled_at TIMESTAMP NULL AFTER last_poll_requested_at'
);
PREPARE stmt FROM @last_polled_at_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_idx_due = (
  SELECT COUNT(*)
  FROM information_schema.statistics
  WHERE table_schema = @schema_name
    AND table_name = 'user_fair_prices'
    AND index_name = 'idx_user_fair_prices_due'
);
SET @idx_due_sql = IF(
  @has_idx_due > 0,
  'SELECT ''idx_user_fair_prices_due already exists''',
  'ALTER TABLE user_fair_prices ADD KEY idx_user_fair_prices_due (enabled, last_polled_at)'
);
PREPARE stmt FROM @idx_due_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_idx_force_poll = (
  SELECT COUNT(*)
  FROM information_schema.statistics
  WHERE table_schema = @schema_name
    AND table_name = 'user_fair_prices'
    AND index_name = 'idx_user_fair_prices_force_poll'
);
SET @idx_force_poll_sql = IF(
  @has_idx_force_poll > 0,
  'SELECT ''idx_user_fair_prices_force_poll already exists''',
  'ALTER TABLE user_fair_prices ADD KEY idx_user_fair_prices_force_poll (force_poll)'
);
PREPARE stmt FROM @idx_force_poll_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

UPDATE user_fair_prices
SET search_keyword = CASE
  WHEN product_type = 'MacBook Air' AND chip IS NOT NULL AND TRIM(chip) <> '' THEN CONCAT(LOWER(chip), '맥북에어')
  WHEN chip IS NOT NULL AND TRIM(chip) <> '' AND product_type IS NOT NULL AND TRIM(product_type) <> '' THEN CONCAT(TRIM(product_type), ' ', UPPER(TRIM(chip)))
  WHEN product_type IS NOT NULL AND TRIM(product_type) <> '' THEN TRIM(product_type)
  ELSE '맥북'
END
WHERE search_keyword IS NULL OR TRIM(search_keyword) = '';

UPDATE user_fair_prices
SET poll_interval_seconds = 60
WHERE poll_interval_seconds IS NULL OR poll_interval_seconds <= 0;

UPDATE user_fair_prices
SET
  force_poll = TRUE,
  last_poll_requested_at = CURRENT_TIMESTAMP,
  last_polled_at = NULL
WHERE enabled = TRUE
  AND search_keyword IS NOT NULL
  AND TRIM(search_keyword) <> '';
