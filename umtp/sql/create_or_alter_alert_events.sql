USE UMTP_RB;

CREATE TABLE IF NOT EXISTS alert_events (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(100) NOT NULL,
  watch_rule_id BIGINT UNSIGNED NULL,
  analysis_job_id BIGINT UNSIGNED NULL,
  product_id VARCHAR(100) NULL,
  source VARCHAR(50) NULL,
  url TEXT NOT NULL,
  title VARCHAR(500) NULL,
  product_type VARCHAR(100) NULL,
  chip VARCHAR(50) NULL,
  screen_inch INT NULL,
  ram_gb INT NULL,
  ssd_gb INT NULL,
  price_krw INT NULL,
  fair_price_krw INT NULL,
  target_price_krw INT NULL,
  drop_rate_percent DECIMAL(6,2) NULL,
  alert_drop_rate_percent DECIMAL(6,2) NULL,
  alert_price_direction VARCHAR(32) NULL,
  risk_level VARCHAR(20) NULL,
  risk_score INT NULL,
  risk_keywords TEXT NULL,
  is_exchange_post BOOLEAN NULL,
  trade_type VARCHAR(20) NULL,
  body_excerpt TEXT NULL,
  body_text TEXT NULL,
  analyzed_at TIMESTAMP NULL,
  trigger_reason VARCHAR(100) NULL,
  message TEXT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'pending',
  send_attempts INT NOT NULL DEFAULT 0,
  error_message TEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  sent_at TIMESTAMP NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_alert_events_user (user_id),
  KEY idx_alert_events_status (status),
  KEY idx_alert_events_created_at (created_at),
  KEY idx_alert_events_product (product_id),
  UNIQUE KEY uq_alert_events_user_product (user_id, product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_watch_rule_id
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'watch_rule_id';
SET @sql_watch_rule_id = IF(
  @has_watch_rule_id = 0,
  'ALTER TABLE alert_events ADD COLUMN watch_rule_id BIGINT UNSIGNED NULL AFTER user_id',
  'SELECT "watch_rule_id exists"'
);
PREPARE stmt_watch_rule_id FROM @sql_watch_rule_id;
EXECUTE stmt_watch_rule_id;
DEALLOCATE PREPARE stmt_watch_rule_id;

SELECT COUNT(*) INTO @has_analysis_job_id
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'analysis_job_id';
SET @sql_analysis_job_id = IF(
  @has_analysis_job_id = 0,
  'ALTER TABLE alert_events ADD COLUMN analysis_job_id BIGINT UNSIGNED NULL AFTER watch_rule_id',
  'SELECT "analysis_job_id exists"'
);
PREPARE stmt_analysis_job_id FROM @sql_analysis_job_id;
EXECUTE stmt_analysis_job_id;
DEALLOCATE PREPARE stmt_analysis_job_id;

SELECT COUNT(*) INTO @has_product_id
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'product_id';
SET @sql_product_id = IF(
  @has_product_id = 0,
  'ALTER TABLE alert_events ADD COLUMN product_id VARCHAR(100) NULL AFTER analysis_job_id',
  'SELECT "product_id exists"'
);
PREPARE stmt_product_id FROM @sql_product_id;
EXECUTE stmt_product_id;
DEALLOCATE PREPARE stmt_product_id;

SELECT COUNT(*) INTO @has_url
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'url';
SET @sql_url = IF(
  @has_url = 0,
  'ALTER TABLE alert_events ADD COLUMN url TEXT NOT NULL AFTER product_id',
  'SELECT "url exists"'
);
PREPARE stmt_url FROM @sql_url;
EXECUTE stmt_url;
DEALLOCATE PREPARE stmt_url;

SELECT COUNT(*) INTO @has_title
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'title';
SET @sql_title = IF(
  @has_title = 0,
  'ALTER TABLE alert_events ADD COLUMN title VARCHAR(500) NULL AFTER url',
  'SELECT "title exists"'
);
PREPARE stmt_title FROM @sql_title;
EXECUTE stmt_title;
DEALLOCATE PREPARE stmt_title;

SELECT COUNT(*) INTO @has_price_krw
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'price_krw';
SET @sql_price_krw = IF(
  @has_price_krw = 0,
  'ALTER TABLE alert_events ADD COLUMN price_krw INT NULL AFTER title',
  'SELECT "price_krw exists"'
);
PREPARE stmt_price_krw FROM @sql_price_krw;
EXECUTE stmt_price_krw;
DEALLOCATE PREPARE stmt_price_krw;

SELECT COUNT(*) INTO @has_fair_price_krw
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'fair_price_krw';
SET @sql_fair_price_krw = IF(
  @has_fair_price_krw = 0,
  'ALTER TABLE alert_events ADD COLUMN fair_price_krw INT NULL AFTER price_krw',
  'SELECT "fair_price_krw exists"'
);
PREPARE stmt_fair_price_krw FROM @sql_fair_price_krw;
EXECUTE stmt_fair_price_krw;
DEALLOCATE PREPARE stmt_fair_price_krw;

SELECT COUNT(*) INTO @has_target_price_krw
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'target_price_krw';
SET @sql_target_price_krw = IF(
  @has_target_price_krw = 0,
  'ALTER TABLE alert_events ADD COLUMN target_price_krw INT NULL AFTER fair_price_krw',
  'SELECT "target_price_krw exists"'
);
PREPARE stmt_target_price_krw FROM @sql_target_price_krw;
EXECUTE stmt_target_price_krw;
DEALLOCATE PREPARE stmt_target_price_krw;

SELECT COUNT(*) INTO @has_drop_rate_percent
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'drop_rate_percent';
SET @sql_drop_rate_percent = IF(
  @has_drop_rate_percent = 0,
  'ALTER TABLE alert_events ADD COLUMN drop_rate_percent DECIMAL(6,2) NULL AFTER target_price_krw',
  'SELECT "drop_rate_percent exists"'
);
PREPARE stmt_drop_rate_percent FROM @sql_drop_rate_percent;
EXECUTE stmt_drop_rate_percent;
DEALLOCATE PREPARE stmt_drop_rate_percent;

SELECT COUNT(*) INTO @has_trigger_reason
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'trigger_reason';
SET @sql_trigger_reason = IF(
  @has_trigger_reason = 0,
  'ALTER TABLE alert_events ADD COLUMN trigger_reason VARCHAR(100) NULL AFTER drop_rate_percent',
  'SELECT "trigger_reason exists"'
);
PREPARE stmt_trigger_reason FROM @sql_trigger_reason;
EXECUTE stmt_trigger_reason;
DEALLOCATE PREPARE stmt_trigger_reason;

SELECT COUNT(*) INTO @has_message
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'message';
SET @sql_message = IF(
  @has_message = 0,
  'ALTER TABLE alert_events ADD COLUMN message TEXT NULL AFTER trigger_reason',
  'SELECT "message exists"'
);
PREPARE stmt_message FROM @sql_message;
EXECUTE stmt_message;
DEALLOCATE PREPARE stmt_message;

SELECT COUNT(*) INTO @has_status
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'status';
SET @sql_status = IF(
  @has_status = 0,
  'ALTER TABLE alert_events ADD COLUMN status VARCHAR(30) NOT NULL DEFAULT "pending" AFTER message',
  'SELECT "status exists"'
);
PREPARE stmt_status FROM @sql_status;
EXECUTE stmt_status;
DEALLOCATE PREPARE stmt_status;

SELECT COUNT(*) INTO @has_send_attempts
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'send_attempts';
SET @sql_send_attempts = IF(
  @has_send_attempts = 0,
  'ALTER TABLE alert_events ADD COLUMN send_attempts INT NOT NULL DEFAULT 0 AFTER status',
  'SELECT "send_attempts exists"'
);
PREPARE stmt_send_attempts FROM @sql_send_attempts;
EXECUTE stmt_send_attempts;
DEALLOCATE PREPARE stmt_send_attempts;

SELECT COUNT(*) INTO @has_error_message
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'error_message';
SET @sql_error_message = IF(
  @has_error_message = 0,
  'ALTER TABLE alert_events ADD COLUMN error_message TEXT NULL AFTER send_attempts',
  'SELECT "error_message exists"'
);
PREPARE stmt_error_message FROM @sql_error_message;
EXECUTE stmt_error_message;
DEALLOCATE PREPARE stmt_error_message;

SELECT COUNT(*) INTO @has_sent_at
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'sent_at';
SET @sql_sent_at = IF(
  @has_sent_at = 0,
  'ALTER TABLE alert_events ADD COLUMN sent_at TIMESTAMP NULL AFTER created_at',
  'SELECT "sent_at exists"'
);
PREPARE stmt_sent_at FROM @sql_sent_at;
EXECUTE stmt_sent_at;
DEALLOCATE PREPARE stmt_sent_at;

SELECT COUNT(*) INTO @has_updated_at
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'updated_at';
SET @sql_updated_at = IF(
  @has_updated_at = 0,
  'ALTER TABLE alert_events ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER sent_at',
  'SELECT "updated_at exists"'
);
PREPARE stmt_updated_at FROM @sql_updated_at;
EXECUTE stmt_updated_at;
DEALLOCATE PREPARE stmt_updated_at;

SELECT COUNT(*) INTO @has_idx_user
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND INDEX_NAME = 'idx_alert_events_user';
SET @sql_idx_user = IF(
  @has_idx_user = 0,
  'ALTER TABLE alert_events ADD INDEX idx_alert_events_user (user_id)',
  'SELECT "idx_alert_events_user exists"'
);
PREPARE stmt_idx_user FROM @sql_idx_user;
EXECUTE stmt_idx_user;
DEALLOCATE PREPARE stmt_idx_user;

SELECT COUNT(*) INTO @has_idx_status
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND INDEX_NAME = 'idx_alert_events_status';
SET @sql_idx_status = IF(
  @has_idx_status = 0,
  'ALTER TABLE alert_events ADD INDEX idx_alert_events_status (status)',
  'SELECT "idx_alert_events_status exists"'
);
PREPARE stmt_idx_status FROM @sql_idx_status;
EXECUTE stmt_idx_status;
DEALLOCATE PREPARE stmt_idx_status;

SELECT COUNT(*) INTO @has_idx_created_at
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND INDEX_NAME = 'idx_alert_events_created_at';
SET @sql_idx_created_at = IF(
  @has_idx_created_at = 0,
  'ALTER TABLE alert_events ADD INDEX idx_alert_events_created_at (created_at)',
  'SELECT "idx_alert_events_created_at exists"'
);
PREPARE stmt_idx_created_at FROM @sql_idx_created_at;
EXECUTE stmt_idx_created_at;
DEALLOCATE PREPARE stmt_idx_created_at;

SELECT COUNT(*) INTO @has_idx_product
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND INDEX_NAME = 'idx_alert_events_product';
SET @sql_idx_product = IF(
  @has_idx_product = 0,
  'ALTER TABLE alert_events ADD INDEX idx_alert_events_product (product_id)',
  'SELECT "idx_alert_events_product exists"'
);
PREPARE stmt_idx_product FROM @sql_idx_product;
EXECUTE stmt_idx_product;
DEALLOCATE PREPARE stmt_idx_product;

SELECT COUNT(*) INTO @has_uq_user_product
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND INDEX_NAME = 'uq_alert_events_user_product';
SET @sql_uq_user_product = IF(
  @has_uq_user_product = 0,
  'ALTER TABLE alert_events ADD UNIQUE KEY uq_alert_events_user_product (user_id, product_id)',
  'SELECT \"uq_alert_events_user_product exists\"'
);
PREPARE stmt_uq_user_product FROM @sql_uq_user_product;
EXECUTE stmt_uq_user_product;
DEALLOCATE PREPARE stmt_uq_user_product;
