USE UMTP_RB;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_fraud_probability
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'fraud_probability';
SET @sql_fraud_probability = IF(
  @has_fraud_probability = 0,
  'ALTER TABLE alert_events ADD COLUMN fraud_probability DECIMAL(6,5) NULL AFTER risk_score',
  'SELECT "fraud_probability exists"'
);
PREPARE stmt_fraud_probability FROM @sql_fraud_probability;
EXECUTE stmt_fraud_probability;
DEALLOCATE PREPARE stmt_fraud_probability;

SELECT COUNT(*) INTO @has_fraud_probability_label
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'fraud_probability_label';
SET @sql_fraud_probability_label = IF(
  @has_fraud_probability_label = 0,
  'ALTER TABLE alert_events ADD COLUMN fraud_probability_label VARCHAR(20) NULL AFTER fraud_probability',
  'SELECT "fraud_probability_label exists"'
);
PREPARE stmt_fraud_probability_label FROM @sql_fraud_probability_label;
EXECUTE stmt_fraud_probability_label;
DEALLOCATE PREPARE stmt_fraud_probability_label;

SELECT COUNT(*) INTO @has_fraud_model_version
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'fraud_model_version';
SET @sql_fraud_model_version = IF(
  @has_fraud_model_version = 0,
  'ALTER TABLE alert_events ADD COLUMN fraud_model_version VARCHAR(100) NULL AFTER fraud_probability_label',
  'SELECT "fraud_model_version exists"'
);
PREPARE stmt_fraud_model_version FROM @sql_fraud_model_version;
EXECUTE stmt_fraud_model_version;
DEALLOCATE PREPARE stmt_fraud_model_version;

SELECT COUNT(*) INTO @has_fraud_scored_at
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'fraud_scored_at';
SET @sql_fraud_scored_at = IF(
  @has_fraud_scored_at = 0,
  'ALTER TABLE alert_events ADD COLUMN fraud_scored_at DATETIME NULL AFTER fraud_model_version',
  'SELECT "fraud_scored_at exists"'
);
PREPARE stmt_fraud_scored_at FROM @sql_fraud_scored_at;
EXECUTE stmt_fraud_scored_at;
DEALLOCATE PREPARE stmt_fraud_scored_at;

SELECT COUNT(*) INTO @has_idx_alert_events_fraud_probability
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND INDEX_NAME = 'idx_alert_events_fraud_probability';
SET @sql_idx_alert_events_fraud_probability = IF(
  @has_idx_alert_events_fraud_probability = 0,
  'ALTER TABLE alert_events ADD INDEX idx_alert_events_fraud_probability (fraud_probability)',
  'SELECT "idx_alert_events_fraud_probability exists"'
);
PREPARE stmt_idx_alert_events_fraud_probability FROM @sql_idx_alert_events_fraud_probability;
EXECUTE stmt_idx_alert_events_fraud_probability;
DEALLOCATE PREPARE stmt_idx_alert_events_fraud_probability;
