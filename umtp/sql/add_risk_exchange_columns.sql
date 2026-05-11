USE UMTP_RB;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_risk_detected
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'risk_detected';
SET @sql_risk_detected = IF(
  @has_risk_detected = 0,
  'ALTER TABLE url_analysis_logs ADD COLUMN risk_detected BOOLEAN NULL AFTER unit_validation_reason',
  'SELECT "risk_detected already exists"'
);
PREPARE stmt_risk_detected FROM @sql_risk_detected;
EXECUTE stmt_risk_detected;
DEALLOCATE PREPARE stmt_risk_detected;

SELECT COUNT(*) INTO @has_risk_level
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'risk_level';
SET @sql_risk_level = IF(
  @has_risk_level = 0,
  'ALTER TABLE url_analysis_logs ADD COLUMN risk_level VARCHAR(20) NULL AFTER risk_detected',
  'SELECT "risk_level already exists"'
);
PREPARE stmt_risk_level FROM @sql_risk_level;
EXECUTE stmt_risk_level;
DEALLOCATE PREPARE stmt_risk_level;

SELECT COUNT(*) INTO @has_risk_score
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'risk_score';
SET @sql_risk_score = IF(
  @has_risk_score = 0,
  'ALTER TABLE url_analysis_logs ADD COLUMN risk_score INT NULL AFTER risk_level',
  'SELECT "risk_score already exists"'
);
PREPARE stmt_risk_score FROM @sql_risk_score;
EXECUTE stmt_risk_score;
DEALLOCATE PREPARE stmt_risk_score;

SELECT COUNT(*) INTO @has_risk_keywords
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'risk_keywords';
SET @sql_risk_keywords = IF(
  @has_risk_keywords = 0,
  'ALTER TABLE url_analysis_logs ADD COLUMN risk_keywords TEXT NULL AFTER risk_score',
  'SELECT "risk_keywords already exists"'
);
PREPARE stmt_risk_keywords FROM @sql_risk_keywords;
EXECUTE stmt_risk_keywords;
DEALLOCATE PREPARE stmt_risk_keywords;

SELECT COUNT(*) INTO @has_risk_categories
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'risk_categories';
SET @sql_risk_categories = IF(
  @has_risk_categories = 0,
  'ALTER TABLE url_analysis_logs ADD COLUMN risk_categories TEXT NULL AFTER risk_keywords',
  'SELECT "risk_categories already exists"'
);
PREPARE stmt_risk_categories FROM @sql_risk_categories;
EXECUTE stmt_risk_categories;
DEALLOCATE PREPARE stmt_risk_categories;

SELECT COUNT(*) INTO @has_is_exchange_post
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'is_exchange_post';
SET @sql_is_exchange_post = IF(
  @has_is_exchange_post = 0,
  'ALTER TABLE url_analysis_logs ADD COLUMN is_exchange_post BOOLEAN NULL AFTER risk_categories',
  'SELECT "is_exchange_post already exists"'
);
PREPARE stmt_is_exchange_post FROM @sql_is_exchange_post;
EXECUTE stmt_is_exchange_post;
DEALLOCATE PREPARE stmt_is_exchange_post;

SELECT COUNT(*) INTO @has_exchange_strength
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'exchange_strength';
SET @sql_exchange_strength = IF(
  @has_exchange_strength = 0,
  'ALTER TABLE url_analysis_logs ADD COLUMN exchange_strength VARCHAR(20) NULL AFTER is_exchange_post',
  'SELECT "exchange_strength already exists"'
);
PREPARE stmt_exchange_strength FROM @sql_exchange_strength;
EXECUTE stmt_exchange_strength;
DEALLOCATE PREPARE stmt_exchange_strength;

SELECT COUNT(*) INTO @has_exchange_keywords
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'exchange_keywords';
SET @sql_exchange_keywords = IF(
  @has_exchange_keywords = 0,
  'ALTER TABLE url_analysis_logs ADD COLUMN exchange_keywords TEXT NULL AFTER exchange_strength',
  'SELECT "exchange_keywords already exists"'
);
PREPARE stmt_exchange_keywords FROM @sql_exchange_keywords;
EXECUTE stmt_exchange_keywords;
DEALLOCATE PREPARE stmt_exchange_keywords;

SELECT COUNT(*) INTO @has_trade_type
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'trade_type';
SET @sql_trade_type = IF(
  @has_trade_type = 0,
  'ALTER TABLE url_analysis_logs ADD COLUMN trade_type VARCHAR(20) NULL AFTER exchange_keywords',
  'SELECT "trade_type already exists"'
);
PREPARE stmt_trade_type FROM @sql_trade_type;
EXECUTE stmt_trade_type;
DEALLOCATE PREPARE stmt_trade_type;
