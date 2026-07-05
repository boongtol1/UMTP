USE UMTP_RB;

CREATE TABLE IF NOT EXISTS alert_events (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(100) NOT NULL,
  watch_rule_id BIGINT UNSIGNED NULL,
  analysis_job_id BIGINT UNSIGNED NULL,
  product_id VARCHAR(100) NULL,
  seller_store_seq BIGINT NULL,
  seller_store_name VARCHAR(100) NULL,
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
  fraud_probability DECIMAL(6,5) NULL,
  fraud_probability_label VARCHAR(20) NULL,
  fraud_model_version VARCHAR(100) NULL,
  fraud_scored_at DATETIME NULL,
  fraud_probability_v1 DECIMAL(6,5) NULL,
  fraud_probability_label_v1 VARCHAR(20) NULL,
  fraud_model_version_v1 VARCHAR(100) NULL,
  fraud_scored_at_v1 DATETIME NULL,
  fraud_probability_v2 DECIMAL(6,5) NULL,
  fraud_probability_label_v2 VARCHAR(20) NULL,
  fraud_model_version_v2 VARCHAR(100) NULL,
  fraud_scored_at_v2 DATETIME NULL,
  risk_keywords TEXT NULL,
  is_exchange_post BOOLEAN NULL,
  trade_type VARCHAR(20) NULL,
  body_excerpt TEXT NULL,
  body_text TEXT NULL,
  sort_date DATETIME NULL,
  analyzed_at TIMESTAMP NULL,
  trigger_reason VARCHAR(100) NULL,
  change_fingerprint VARCHAR(64) NOT NULL DEFAULT '',
  message TEXT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'pending',
  send_attempts INT NOT NULL DEFAULT 0,
  error_message TEXT NULL,
  is_read TINYINT(1) NOT NULL DEFAULT 0,
  read_at DATETIME NULL,
  is_read_archive_cleared TINYINT(1) NOT NULL DEFAULT 0,
  read_archive_cleared_at DATETIME NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  sent_at TIMESTAMP NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_alert_events_user (user_id),
  KEY idx_alert_events_user_is_read (user_id, is_read, read_at),
  KEY idx_alert_events_user_read_archive_clear (user_id, is_read, is_read_archive_cleared, read_archive_cleared_at),
  KEY idx_alert_events_status (status),
  KEY idx_alert_events_created_at (created_at),
  KEY idx_alert_events_product (product_id),
  KEY idx_alert_events_sort_date (sort_date),
  UNIQUE KEY uq_alert_events_user_rule_product (user_id, watch_rule_id, product_id, change_fingerprint)
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

SELECT COUNT(*) INTO @has_seller_store_seq
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'seller_store_seq';
SET @sql_seller_store_seq = IF(
  @has_seller_store_seq = 0,
  'ALTER TABLE alert_events ADD COLUMN seller_store_seq BIGINT NULL AFTER product_id',
  'SELECT "seller_store_seq exists"'
);
PREPARE stmt_seller_store_seq FROM @sql_seller_store_seq;
EXECUTE stmt_seller_store_seq;
DEALLOCATE PREPARE stmt_seller_store_seq;

SELECT COUNT(*) INTO @has_seller_store_name
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'seller_store_name';
SET @sql_seller_store_name = IF(
  @has_seller_store_name = 0,
  'ALTER TABLE alert_events ADD COLUMN seller_store_name VARCHAR(100) NULL AFTER seller_store_seq',
  'SELECT "seller_store_name exists"'
);
PREPARE stmt_seller_store_name FROM @sql_seller_store_name;
EXECUTE stmt_seller_store_name;
DEALLOCATE PREPARE stmt_seller_store_name;

SELECT COUNT(*) INTO @has_sort_date
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'sort_date';
SET @sql_sort_date = IF(
  @has_sort_date = 0,
  'ALTER TABLE alert_events ADD COLUMN sort_date DATETIME NULL AFTER product_id',
  'SELECT "sort_date exists"'
);
PREPARE stmt_sort_date FROM @sql_sort_date;
EXECUTE stmt_sort_date;
DEALLOCATE PREPARE stmt_sort_date;

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

SELECT COUNT(*) INTO @has_change_fingerprint
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'change_fingerprint';
SET @sql_change_fingerprint = IF(
  @has_change_fingerprint = 0,
  'ALTER TABLE alert_events ADD COLUMN change_fingerprint VARCHAR(64) NOT NULL DEFAULT '''' AFTER trigger_reason',
  'SELECT "change_fingerprint exists"'
);
PREPARE stmt_change_fingerprint FROM @sql_change_fingerprint;
EXECUTE stmt_change_fingerprint;
DEALLOCATE PREPARE stmt_change_fingerprint;

SET @sql_backfill_change_fingerprint = '
UPDATE alert_events
SET change_fingerprint = SHA2(
  CONCAT_WS(
    ''|'',
    IFNULL(user_id, ''''),
    IFNULL(CAST(watch_rule_id AS CHAR), ''''),
    IFNULL(product_id, ''''),
    IFNULL(trigger_reason, ''''),
    IFNULL(DATE_FORMAT(sort_date, ''%Y-%m-%d %H:%i:%s''), ''''),
    IFNULL(title, ''''),
    IFNULL(CAST(price_krw AS CHAR), ''''),
    IFNULL(CAST(id AS CHAR), '''')
  ),
  256
)
WHERE change_fingerprint IS NULL OR LENGTH(TRIM(change_fingerprint)) = 0';
PREPARE stmt_backfill_change_fingerprint FROM @sql_backfill_change_fingerprint;
EXECUTE stmt_backfill_change_fingerprint;
DEALLOCATE PREPARE stmt_backfill_change_fingerprint;

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

SELECT COUNT(*) INTO @has_is_read
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'is_read';
SET @sql_is_read = IF(
  @has_is_read = 0,
  'ALTER TABLE alert_events ADD COLUMN is_read TINYINT(1) NOT NULL DEFAULT 0 AFTER error_message',
  'SELECT "is_read exists"'
);
PREPARE stmt_is_read FROM @sql_is_read;
EXECUTE stmt_is_read;
DEALLOCATE PREPARE stmt_is_read;

SELECT COUNT(*) INTO @has_read_at
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'read_at';
SET @sql_read_at = IF(
  @has_read_at = 0,
  'ALTER TABLE alert_events ADD COLUMN read_at DATETIME NULL AFTER is_read',
  'SELECT "read_at exists"'
);
PREPARE stmt_read_at FROM @sql_read_at;
EXECUTE stmt_read_at;
DEALLOCATE PREPARE stmt_read_at;

SELECT COUNT(*) INTO @has_is_read_archive_cleared
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'is_read_archive_cleared';
SET @sql_is_read_archive_cleared = IF(
  @has_is_read_archive_cleared = 0,
  'ALTER TABLE alert_events ADD COLUMN is_read_archive_cleared TINYINT(1) NOT NULL DEFAULT 0 AFTER read_at',
  'SELECT "is_read_archive_cleared exists"'
);
PREPARE stmt_is_read_archive_cleared FROM @sql_is_read_archive_cleared;
EXECUTE stmt_is_read_archive_cleared;
DEALLOCATE PREPARE stmt_is_read_archive_cleared;

SELECT COUNT(*) INTO @has_read_archive_cleared_at
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'read_archive_cleared_at';
SET @sql_read_archive_cleared_at = IF(
  @has_read_archive_cleared_at = 0,
  'ALTER TABLE alert_events ADD COLUMN read_archive_cleared_at DATETIME NULL AFTER is_read_archive_cleared',
  'SELECT "read_archive_cleared_at exists"'
);
PREPARE stmt_read_archive_cleared_at FROM @sql_read_archive_cleared_at;
EXECUTE stmt_read_archive_cleared_at;
DEALLOCATE PREPARE stmt_read_archive_cleared_at;

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

SELECT COUNT(*) INTO @has_idx_user_is_read
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND INDEX_NAME = 'idx_alert_events_user_is_read';
SET @sql_idx_user_is_read = IF(
  @has_idx_user_is_read = 0,
  'ALTER TABLE alert_events ADD INDEX idx_alert_events_user_is_read (user_id, is_read, read_at)',
  'SELECT "idx_alert_events_user_is_read exists"'
);
PREPARE stmt_idx_user_is_read FROM @sql_idx_user_is_read;
EXECUTE stmt_idx_user_is_read;
DEALLOCATE PREPARE stmt_idx_user_is_read;

SELECT COUNT(*) INTO @has_idx_user_read_archive_clear
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND INDEX_NAME = 'idx_alert_events_user_read_archive_clear';
SET @sql_idx_user_read_archive_clear = IF(
  @has_idx_user_read_archive_clear = 0,
  'ALTER TABLE alert_events ADD INDEX idx_alert_events_user_read_archive_clear (user_id, is_read, is_read_archive_cleared, read_archive_cleared_at)',
  'SELECT "idx_alert_events_user_read_archive_clear exists"'
);
PREPARE stmt_idx_user_read_archive_clear FROM @sql_idx_user_read_archive_clear;
EXECUTE stmt_idx_user_read_archive_clear;
DEALLOCATE PREPARE stmt_idx_user_read_archive_clear;

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

SELECT COUNT(*) INTO @has_idx_sort_date
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND INDEX_NAME = 'idx_alert_events_sort_date';
SET @sql_idx_sort_date = IF(
  @has_idx_sort_date = 0,
  'ALTER TABLE alert_events ADD INDEX idx_alert_events_sort_date (sort_date)',
  'SELECT "idx_alert_events_sort_date exists"'
);
PREPARE stmt_idx_sort_date FROM @sql_idx_sort_date;
EXECUTE stmt_idx_sort_date;
DEALLOCATE PREPARE stmt_idx_sort_date;

SELECT COUNT(*) INTO @has_uq_user_product
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND INDEX_NAME = 'uq_alert_events_user_product';
SET @sql_drop_uq_user_product = IF(
  @has_uq_user_product = 0,
  'SELECT "uq_alert_events_user_product already absent"',
  'ALTER TABLE alert_events DROP INDEX uq_alert_events_user_product'
);
PREPARE stmt_drop_uq_user_product FROM @sql_drop_uq_user_product;
EXECUTE stmt_drop_uq_user_product;
DEALLOCATE PREPARE stmt_drop_uq_user_product;

SELECT COUNT(*) INTO @has_uq_user_rule_product
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND INDEX_NAME = 'uq_alert_events_user_rule_product';

SELECT GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX SEPARATOR ',')
INTO @uq_alert_events_user_rule_product_cols
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND INDEX_NAME = 'uq_alert_events_user_rule_product';

SET @sql_drop_uq_user_rule_product_mismatch = IF(
  @has_uq_user_rule_product > 0
  AND IFNULL(@uq_alert_events_user_rule_product_cols, '') <> 'user_id,watch_rule_id,product_id,change_fingerprint',
  'ALTER TABLE alert_events DROP INDEX uq_alert_events_user_rule_product',
  'SELECT "uq_alert_events_user_rule_product definition ok"'
);
PREPARE stmt_drop_uq_user_rule_product_mismatch FROM @sql_drop_uq_user_rule_product_mismatch;
EXECUTE stmt_drop_uq_user_rule_product_mismatch;
DEALLOCATE PREPARE stmt_drop_uq_user_rule_product_mismatch;

SELECT COUNT(*) INTO @has_uq_user_rule_product_after_drop
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND INDEX_NAME = 'uq_alert_events_user_rule_product';
SET @sql_uq_user_rule_product = IF(
  @has_uq_user_rule_product_after_drop = 0,
  'ALTER TABLE alert_events ADD UNIQUE KEY uq_alert_events_user_rule_product (user_id, watch_rule_id, product_id, change_fingerprint)',
  'SELECT "uq_alert_events_user_rule_product exists"'
);
PREPARE stmt_uq_user_rule_product FROM @sql_uq_user_rule_product;
EXECUTE stmt_uq_user_rule_product;
DEALLOCATE PREPARE stmt_uq_user_rule_product;
