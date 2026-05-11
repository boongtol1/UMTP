USE UMTP_RB;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_confidence_score
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'confidence_score';
SET @sql_confidence_score = IF(
  @has_confidence_score = 0,
  'ALTER TABLE url_analysis_logs ADD COLUMN confidence_score INT NULL AFTER reason',
  'SELECT "confidence_score already exists"'
);
PREPARE stmt_confidence_score FROM @sql_confidence_score;
EXECUTE stmt_confidence_score;
DEALLOCATE PREPARE stmt_confidence_score;

SELECT COUNT(*) INTO @has_screen_inch_defaulted
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'screen_inch_defaulted';
SET @sql_screen_inch_defaulted = IF(
  @has_screen_inch_defaulted = 0,
  'ALTER TABLE url_analysis_logs ADD COLUMN screen_inch_defaulted BOOLEAN NULL AFTER confidence_score',
  'SELECT "screen_inch_defaulted already exists"'
);
PREPARE stmt_screen_inch_defaulted FROM @sql_screen_inch_defaulted;
EXECUTE stmt_screen_inch_defaulted;
DEALLOCATE PREPARE stmt_screen_inch_defaulted;

SELECT COUNT(*) INTO @has_unit_valid
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'unit_valid';
SET @sql_unit_valid = IF(
  @has_unit_valid = 0,
  'ALTER TABLE url_analysis_logs ADD COLUMN unit_valid BOOLEAN NULL AFTER screen_inch_defaulted',
  'SELECT "unit_valid already exists"'
);
PREPARE stmt_unit_valid FROM @sql_unit_valid;
EXECUTE stmt_unit_valid;
DEALLOCATE PREPARE stmt_unit_valid;

SELECT COUNT(*) INTO @has_unit_validation_reason
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'unit_validation_reason';
SET @sql_unit_validation_reason = IF(
  @has_unit_validation_reason = 0,
  'ALTER TABLE url_analysis_logs ADD COLUMN unit_validation_reason VARCHAR(64) NULL AFTER unit_valid',
  'SELECT "unit_validation_reason already exists"'
);
PREPARE stmt_unit_validation_reason FROM @sql_unit_validation_reason;
EXECUTE stmt_unit_validation_reason;
DEALLOCATE PREPARE stmt_unit_validation_reason;
