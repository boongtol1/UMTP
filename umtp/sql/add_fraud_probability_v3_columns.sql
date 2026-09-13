USE UMTP_RB;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_fraud_probability_v3
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'fraud_probability_v3';
SET @sql_fraud_probability_v3 = IF(
  @has_fraud_probability_v3 = 0,
  'ALTER TABLE alert_events ADD COLUMN fraud_probability_v3 DECIMAL(6,5) NULL AFTER fraud_scored_at_v2',
  'SELECT "fraud_probability_v3 exists"'
);
PREPARE stmt_fraud_probability_v3 FROM @sql_fraud_probability_v3;
EXECUTE stmt_fraud_probability_v3;
DEALLOCATE PREPARE stmt_fraud_probability_v3;

SELECT COUNT(*) INTO @has_fraud_probability_label_v3
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'fraud_probability_label_v3';
SET @sql_fraud_probability_label_v3 = IF(
  @has_fraud_probability_label_v3 = 0,
  'ALTER TABLE alert_events ADD COLUMN fraud_probability_label_v3 VARCHAR(20) NULL AFTER fraud_probability_v3',
  'SELECT "fraud_probability_label_v3 exists"'
);
PREPARE stmt_fraud_probability_label_v3 FROM @sql_fraud_probability_label_v3;
EXECUTE stmt_fraud_probability_label_v3;
DEALLOCATE PREPARE stmt_fraud_probability_label_v3;

SELECT COUNT(*) INTO @has_fraud_model_version_v3
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'fraud_model_version_v3';
SET @sql_fraud_model_version_v3 = IF(
  @has_fraud_model_version_v3 = 0,
  'ALTER TABLE alert_events ADD COLUMN fraud_model_version_v3 VARCHAR(100) NULL AFTER fraud_probability_label_v3',
  'SELECT "fraud_model_version_v3 exists"'
);
PREPARE stmt_fraud_model_version_v3 FROM @sql_fraud_model_version_v3;
EXECUTE stmt_fraud_model_version_v3;
DEALLOCATE PREPARE stmt_fraud_model_version_v3;

SELECT COUNT(*) INTO @has_fraud_scored_at_v3
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'fraud_scored_at_v3';
SET @sql_fraud_scored_at_v3 = IF(
  @has_fraud_scored_at_v3 = 0,
  'ALTER TABLE alert_events ADD COLUMN fraud_scored_at_v3 DATETIME NULL AFTER fraud_model_version_v3',
  'SELECT "fraud_scored_at_v3 exists"'
);
PREPARE stmt_fraud_scored_at_v3 FROM @sql_fraud_scored_at_v3;
EXECUTE stmt_fraud_scored_at_v3;
DEALLOCATE PREPARE stmt_fraud_scored_at_v3;

SELECT COUNT(*) INTO @has_idx_alert_events_fraud_probability_v3
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND INDEX_NAME = 'idx_alert_events_fraud_probability_v3';
SET @sql_idx_alert_events_fraud_probability_v3 = IF(
  @has_idx_alert_events_fraud_probability_v3 = 0,
  'ALTER TABLE alert_events ADD INDEX idx_alert_events_fraud_probability_v3 (fraud_probability_v3)',
  'SELECT "idx_alert_events_fraud_probability_v3 exists"'
);
PREPARE stmt_idx_alert_events_fraud_probability_v3 FROM @sql_idx_alert_events_fraud_probability_v3;
EXECUTE stmt_idx_alert_events_fraud_probability_v3;
DEALLOCATE PREPARE stmt_idx_alert_events_fraud_probability_v3;
