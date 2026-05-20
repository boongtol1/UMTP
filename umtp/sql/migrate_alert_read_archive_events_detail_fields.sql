USE UMTP_RB;

CREATE TABLE IF NOT EXISTS alert_read_archive_events (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id VARCHAR(100) NOT NULL,
  alert_event_id BIGINT UNSIGNED NULL,
  action_type VARCHAR(50) NOT NULL,
  requested_count INT NULL,
  affected_count INT NULL,
  skipped_count INT NULL,
  not_found_ids_json TEXT NULL,
  reason VARCHAR(100) NULL,
  metadata_json LONGTEXT NULL,
  alert_trigger_reason VARCHAR(100) NULL,
  alert_condition_label VARCHAR(100) NULL,
  alert_source VARCHAR(50) NULL,
  alert_url TEXT NULL,
  alert_listing_image_url TEXT NULL,
  alert_title VARCHAR(500) NULL,
  alert_product_id VARCHAR(100) NULL,
  alert_sort_date DATETIME NULL,
  alert_product_type VARCHAR(100) NULL,
  alert_chip VARCHAR(50) NULL,
  alert_screen_inch INT NULL,
  alert_ram_gb INT NULL,
  alert_ssd_gb INT NULL,
  alert_price_krw INT NULL,
  alert_fair_price_krw INT NULL,
  alert_target_price_krw INT NULL,
  alert_drop_rate_percent DECIMAL(10,2) NULL,
  alert_rule_drop_rate_percent DECIMAL(10,2) NULL,
  alert_price_direction VARCHAR(32) NULL,
  alert_risk_level VARCHAR(20) NULL,
  alert_risk_label VARCHAR(20) NULL,
  alert_risk_score INT NULL,
  alert_risk_keywords TEXT NULL,
  alert_trade_type VARCHAR(20) NULL,
  alert_is_exchange_post TINYINT(1) NULL,
  alert_trade_flags_text VARCHAR(100) NULL,
  alert_special_notes_text TEXT NULL,
  alert_body_excerpt TEXT NULL,
  alert_body_text LONGTEXT NULL,
  alert_message TEXT NULL,
  alert_status VARCHAR(30) NULL,
  alert_analyzed_at DATETIME NULL,
  alert_created_at DATETIME NULL,
  alert_sent_at DATETIME NULL,
  alert_updated_at DATETIME NULL,
  alert_read_at DATETIME NULL,
  alert_payload_json LONGTEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_alert_read_archive_events_user_created_at (user_id, created_at),
  KEY idx_alert_read_archive_events_action_created_at (action_type, created_at),
  KEY idx_alert_read_archive_events_alert_event_id (alert_event_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_alert_trigger_reason
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_trigger_reason';
SET @sql_alert_trigger_reason = IF(@has_alert_trigger_reason = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_trigger_reason VARCHAR(100) NULL AFTER metadata_json', 'SELECT "alert_trigger_reason exists"');
PREPARE stmt_alert_trigger_reason FROM @sql_alert_trigger_reason; EXECUTE stmt_alert_trigger_reason; DEALLOCATE PREPARE stmt_alert_trigger_reason;

SELECT COUNT(*) INTO @has_alert_condition_label
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_condition_label';
SET @sql_alert_condition_label = IF(@has_alert_condition_label = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_condition_label VARCHAR(100) NULL AFTER alert_trigger_reason', 'SELECT "alert_condition_label exists"');
PREPARE stmt_alert_condition_label FROM @sql_alert_condition_label; EXECUTE stmt_alert_condition_label; DEALLOCATE PREPARE stmt_alert_condition_label;

SELECT COUNT(*) INTO @has_alert_source
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_source';
SET @sql_alert_source = IF(@has_alert_source = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_source VARCHAR(50) NULL AFTER alert_condition_label', 'SELECT "alert_source exists"');
PREPARE stmt_alert_source FROM @sql_alert_source; EXECUTE stmt_alert_source; DEALLOCATE PREPARE stmt_alert_source;

SELECT COUNT(*) INTO @has_alert_url
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_url';
SET @sql_alert_url = IF(@has_alert_url = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_url TEXT NULL AFTER alert_source', 'SELECT "alert_url exists"');
PREPARE stmt_alert_url FROM @sql_alert_url; EXECUTE stmt_alert_url; DEALLOCATE PREPARE stmt_alert_url;

SELECT COUNT(*) INTO @has_alert_listing_image_url
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_listing_image_url';
SET @sql_alert_listing_image_url = IF(@has_alert_listing_image_url = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_listing_image_url TEXT NULL AFTER alert_url', 'SELECT "alert_listing_image_url exists"');
PREPARE stmt_alert_listing_image_url FROM @sql_alert_listing_image_url; EXECUTE stmt_alert_listing_image_url; DEALLOCATE PREPARE stmt_alert_listing_image_url;

SELECT COUNT(*) INTO @has_alert_title
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_title';
SET @sql_alert_title = IF(@has_alert_title = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_title VARCHAR(500) NULL AFTER alert_listing_image_url', 'SELECT "alert_title exists"');
PREPARE stmt_alert_title FROM @sql_alert_title; EXECUTE stmt_alert_title; DEALLOCATE PREPARE stmt_alert_title;

SELECT COUNT(*) INTO @has_alert_product_id
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_product_id';
SET @sql_alert_product_id = IF(@has_alert_product_id = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_product_id VARCHAR(100) NULL AFTER alert_title', 'SELECT "alert_product_id exists"');
PREPARE stmt_alert_product_id FROM @sql_alert_product_id; EXECUTE stmt_alert_product_id; DEALLOCATE PREPARE stmt_alert_product_id;

SELECT COUNT(*) INTO @has_alert_sort_date
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_sort_date';
SET @sql_alert_sort_date = IF(@has_alert_sort_date = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_sort_date DATETIME NULL AFTER alert_product_id', 'SELECT "alert_sort_date exists"');
PREPARE stmt_alert_sort_date FROM @sql_alert_sort_date; EXECUTE stmt_alert_sort_date; DEALLOCATE PREPARE stmt_alert_sort_date;

SELECT COUNT(*) INTO @has_alert_product_type
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_product_type';
SET @sql_alert_product_type = IF(@has_alert_product_type = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_product_type VARCHAR(100) NULL AFTER alert_sort_date', 'SELECT "alert_product_type exists"');
PREPARE stmt_alert_product_type FROM @sql_alert_product_type; EXECUTE stmt_alert_product_type; DEALLOCATE PREPARE stmt_alert_product_type;

SELECT COUNT(*) INTO @has_alert_chip
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_chip';
SET @sql_alert_chip = IF(@has_alert_chip = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_chip VARCHAR(50) NULL AFTER alert_product_type', 'SELECT "alert_chip exists"');
PREPARE stmt_alert_chip FROM @sql_alert_chip; EXECUTE stmt_alert_chip; DEALLOCATE PREPARE stmt_alert_chip;

SELECT COUNT(*) INTO @has_alert_screen_inch
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_screen_inch';
SET @sql_alert_screen_inch = IF(@has_alert_screen_inch = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_screen_inch INT NULL AFTER alert_chip', 'SELECT "alert_screen_inch exists"');
PREPARE stmt_alert_screen_inch FROM @sql_alert_screen_inch; EXECUTE stmt_alert_screen_inch; DEALLOCATE PREPARE stmt_alert_screen_inch;

SELECT COUNT(*) INTO @has_alert_ram_gb
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_ram_gb';
SET @sql_alert_ram_gb = IF(@has_alert_ram_gb = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_ram_gb INT NULL AFTER alert_screen_inch', 'SELECT "alert_ram_gb exists"');
PREPARE stmt_alert_ram_gb FROM @sql_alert_ram_gb; EXECUTE stmt_alert_ram_gb; DEALLOCATE PREPARE stmt_alert_ram_gb;

SELECT COUNT(*) INTO @has_alert_ssd_gb
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_ssd_gb';
SET @sql_alert_ssd_gb = IF(@has_alert_ssd_gb = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_ssd_gb INT NULL AFTER alert_ram_gb', 'SELECT "alert_ssd_gb exists"');
PREPARE stmt_alert_ssd_gb FROM @sql_alert_ssd_gb; EXECUTE stmt_alert_ssd_gb; DEALLOCATE PREPARE stmt_alert_ssd_gb;

SELECT COUNT(*) INTO @has_alert_price_krw
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_price_krw';
SET @sql_alert_price_krw = IF(@has_alert_price_krw = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_price_krw INT NULL AFTER alert_ssd_gb', 'SELECT "alert_price_krw exists"');
PREPARE stmt_alert_price_krw FROM @sql_alert_price_krw; EXECUTE stmt_alert_price_krw; DEALLOCATE PREPARE stmt_alert_price_krw;

SELECT COUNT(*) INTO @has_alert_fair_price_krw
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_fair_price_krw';
SET @sql_alert_fair_price_krw = IF(@has_alert_fair_price_krw = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_fair_price_krw INT NULL AFTER alert_price_krw', 'SELECT "alert_fair_price_krw exists"');
PREPARE stmt_alert_fair_price_krw FROM @sql_alert_fair_price_krw; EXECUTE stmt_alert_fair_price_krw; DEALLOCATE PREPARE stmt_alert_fair_price_krw;

SELECT COUNT(*) INTO @has_alert_target_price_krw
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_target_price_krw';
SET @sql_alert_target_price_krw = IF(@has_alert_target_price_krw = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_target_price_krw INT NULL AFTER alert_fair_price_krw', 'SELECT "alert_target_price_krw exists"');
PREPARE stmt_alert_target_price_krw FROM @sql_alert_target_price_krw; EXECUTE stmt_alert_target_price_krw; DEALLOCATE PREPARE stmt_alert_target_price_krw;

SELECT COUNT(*) INTO @has_alert_drop_rate_percent
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_drop_rate_percent';
SET @sql_alert_drop_rate_percent = IF(@has_alert_drop_rate_percent = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_drop_rate_percent DECIMAL(10,2) NULL AFTER alert_target_price_krw', 'SELECT "alert_drop_rate_percent exists"');
PREPARE stmt_alert_drop_rate_percent FROM @sql_alert_drop_rate_percent; EXECUTE stmt_alert_drop_rate_percent; DEALLOCATE PREPARE stmt_alert_drop_rate_percent;

SELECT COUNT(*) INTO @has_alert_rule_drop_rate_percent
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_rule_drop_rate_percent';
SET @sql_alert_rule_drop_rate_percent = IF(@has_alert_rule_drop_rate_percent = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_rule_drop_rate_percent DECIMAL(10,2) NULL AFTER alert_drop_rate_percent', 'SELECT "alert_rule_drop_rate_percent exists"');
PREPARE stmt_alert_rule_drop_rate_percent FROM @sql_alert_rule_drop_rate_percent; EXECUTE stmt_alert_rule_drop_rate_percent; DEALLOCATE PREPARE stmt_alert_rule_drop_rate_percent;

SELECT COUNT(*) INTO @has_alert_price_direction
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_price_direction';
SET @sql_alert_price_direction = IF(@has_alert_price_direction = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_price_direction VARCHAR(32) NULL AFTER alert_rule_drop_rate_percent', 'SELECT "alert_price_direction exists"');
PREPARE stmt_alert_price_direction FROM @sql_alert_price_direction; EXECUTE stmt_alert_price_direction; DEALLOCATE PREPARE stmt_alert_price_direction;

SELECT COUNT(*) INTO @has_alert_risk_level
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_risk_level';
SET @sql_alert_risk_level = IF(@has_alert_risk_level = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_risk_level VARCHAR(20) NULL AFTER alert_price_direction', 'SELECT "alert_risk_level exists"');
PREPARE stmt_alert_risk_level FROM @sql_alert_risk_level; EXECUTE stmt_alert_risk_level; DEALLOCATE PREPARE stmt_alert_risk_level;

SELECT COUNT(*) INTO @has_alert_risk_label
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_risk_label';
SET @sql_alert_risk_label = IF(@has_alert_risk_label = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_risk_label VARCHAR(20) NULL AFTER alert_risk_level', 'SELECT "alert_risk_label exists"');
PREPARE stmt_alert_risk_label FROM @sql_alert_risk_label; EXECUTE stmt_alert_risk_label; DEALLOCATE PREPARE stmt_alert_risk_label;

SELECT COUNT(*) INTO @has_alert_risk_score
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_risk_score';
SET @sql_alert_risk_score = IF(@has_alert_risk_score = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_risk_score INT NULL AFTER alert_risk_label', 'SELECT "alert_risk_score exists"');
PREPARE stmt_alert_risk_score FROM @sql_alert_risk_score; EXECUTE stmt_alert_risk_score; DEALLOCATE PREPARE stmt_alert_risk_score;

SELECT COUNT(*) INTO @has_alert_risk_keywords
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_risk_keywords';
SET @sql_alert_risk_keywords = IF(@has_alert_risk_keywords = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_risk_keywords TEXT NULL AFTER alert_risk_score', 'SELECT "alert_risk_keywords exists"');
PREPARE stmt_alert_risk_keywords FROM @sql_alert_risk_keywords; EXECUTE stmt_alert_risk_keywords; DEALLOCATE PREPARE stmt_alert_risk_keywords;

SELECT COUNT(*) INTO @has_alert_trade_type
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_trade_type';
SET @sql_alert_trade_type = IF(@has_alert_trade_type = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_trade_type VARCHAR(20) NULL AFTER alert_risk_keywords', 'SELECT "alert_trade_type exists"');
PREPARE stmt_alert_trade_type FROM @sql_alert_trade_type; EXECUTE stmt_alert_trade_type; DEALLOCATE PREPARE stmt_alert_trade_type;

SELECT COUNT(*) INTO @has_alert_is_exchange_post
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_is_exchange_post';
SET @sql_alert_is_exchange_post = IF(@has_alert_is_exchange_post = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_is_exchange_post TINYINT(1) NULL AFTER alert_trade_type', 'SELECT "alert_is_exchange_post exists"');
PREPARE stmt_alert_is_exchange_post FROM @sql_alert_is_exchange_post; EXECUTE stmt_alert_is_exchange_post; DEALLOCATE PREPARE stmt_alert_is_exchange_post;

SELECT COUNT(*) INTO @has_alert_trade_flags_text
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_trade_flags_text';
SET @sql_alert_trade_flags_text = IF(@has_alert_trade_flags_text = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_trade_flags_text VARCHAR(100) NULL AFTER alert_is_exchange_post', 'SELECT "alert_trade_flags_text exists"');
PREPARE stmt_alert_trade_flags_text FROM @sql_alert_trade_flags_text; EXECUTE stmt_alert_trade_flags_text; DEALLOCATE PREPARE stmt_alert_trade_flags_text;

SELECT COUNT(*) INTO @has_alert_special_notes_text
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_special_notes_text';
SET @sql_alert_special_notes_text = IF(@has_alert_special_notes_text = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_special_notes_text TEXT NULL AFTER alert_trade_flags_text', 'SELECT "alert_special_notes_text exists"');
PREPARE stmt_alert_special_notes_text FROM @sql_alert_special_notes_text; EXECUTE stmt_alert_special_notes_text; DEALLOCATE PREPARE stmt_alert_special_notes_text;

SELECT COUNT(*) INTO @has_alert_body_excerpt
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_body_excerpt';
SET @sql_alert_body_excerpt = IF(@has_alert_body_excerpt = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_body_excerpt TEXT NULL AFTER alert_special_notes_text', 'SELECT "alert_body_excerpt exists"');
PREPARE stmt_alert_body_excerpt FROM @sql_alert_body_excerpt; EXECUTE stmt_alert_body_excerpt; DEALLOCATE PREPARE stmt_alert_body_excerpt;

SELECT COUNT(*) INTO @has_alert_body_text
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_body_text';
SET @sql_alert_body_text = IF(@has_alert_body_text = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_body_text LONGTEXT NULL AFTER alert_body_excerpt', 'SELECT "alert_body_text exists"');
PREPARE stmt_alert_body_text FROM @sql_alert_body_text; EXECUTE stmt_alert_body_text; DEALLOCATE PREPARE stmt_alert_body_text;

SELECT COUNT(*) INTO @has_alert_message
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_message';
SET @sql_alert_message = IF(@has_alert_message = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_message TEXT NULL AFTER alert_body_text', 'SELECT "alert_message exists"');
PREPARE stmt_alert_message FROM @sql_alert_message; EXECUTE stmt_alert_message; DEALLOCATE PREPARE stmt_alert_message;

SELECT COUNT(*) INTO @has_alert_status
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_status';
SET @sql_alert_status = IF(@has_alert_status = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_status VARCHAR(30) NULL AFTER alert_message', 'SELECT "alert_status exists"');
PREPARE stmt_alert_status FROM @sql_alert_status; EXECUTE stmt_alert_status; DEALLOCATE PREPARE stmt_alert_status;

SELECT COUNT(*) INTO @has_alert_analyzed_at
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_analyzed_at';
SET @sql_alert_analyzed_at = IF(@has_alert_analyzed_at = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_analyzed_at DATETIME NULL AFTER alert_status', 'SELECT "alert_analyzed_at exists"');
PREPARE stmt_alert_analyzed_at FROM @sql_alert_analyzed_at; EXECUTE stmt_alert_analyzed_at; DEALLOCATE PREPARE stmt_alert_analyzed_at;

SELECT COUNT(*) INTO @has_alert_created_at
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_created_at';
SET @sql_alert_created_at = IF(@has_alert_created_at = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_created_at DATETIME NULL AFTER alert_analyzed_at', 'SELECT "alert_created_at exists"');
PREPARE stmt_alert_created_at FROM @sql_alert_created_at; EXECUTE stmt_alert_created_at; DEALLOCATE PREPARE stmt_alert_created_at;

SELECT COUNT(*) INTO @has_alert_sent_at
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_sent_at';
SET @sql_alert_sent_at = IF(@has_alert_sent_at = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_sent_at DATETIME NULL AFTER alert_created_at', 'SELECT "alert_sent_at exists"');
PREPARE stmt_alert_sent_at FROM @sql_alert_sent_at; EXECUTE stmt_alert_sent_at; DEALLOCATE PREPARE stmt_alert_sent_at;

SELECT COUNT(*) INTO @has_alert_updated_at
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_updated_at';
SET @sql_alert_updated_at = IF(@has_alert_updated_at = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_updated_at DATETIME NULL AFTER alert_sent_at', 'SELECT "alert_updated_at exists"');
PREPARE stmt_alert_updated_at FROM @sql_alert_updated_at; EXECUTE stmt_alert_updated_at; DEALLOCATE PREPARE stmt_alert_updated_at;

SELECT COUNT(*) INTO @has_alert_read_at
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_read_at';
SET @sql_alert_read_at = IF(@has_alert_read_at = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_read_at DATETIME NULL AFTER alert_updated_at', 'SELECT "alert_read_at exists"');
PREPARE stmt_alert_read_at FROM @sql_alert_read_at; EXECUTE stmt_alert_read_at; DEALLOCATE PREPARE stmt_alert_read_at;

SELECT COUNT(*) INTO @has_alert_payload_json
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'alert_read_archive_events' AND COLUMN_NAME = 'alert_payload_json';
SET @sql_alert_payload_json = IF(@has_alert_payload_json = 0, 'ALTER TABLE alert_read_archive_events ADD COLUMN alert_payload_json LONGTEXT NULL AFTER alert_read_at', 'SELECT "alert_payload_json exists"');
PREPARE stmt_alert_payload_json FROM @sql_alert_payload_json; EXECUTE stmt_alert_payload_json; DEALLOCATE PREPARE stmt_alert_payload_json;
