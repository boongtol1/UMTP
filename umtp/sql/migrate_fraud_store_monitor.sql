USE UMTP_RB;

CREATE TABLE IF NOT EXISTS fraud_store_status_snapshots (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  store_id VARCHAR(64) NOT NULL,
  store_seq BIGINT NULL,
  checked_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  status VARCHAR(50) NOT NULL DEFAULT 'unknown',
  status_reason VARCHAR(100) NULL,
  source VARCHAR(50) NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 0,
  http_status INT NULL,
  meta_code INT NULL,
  meta_message VARCHAR(255) NULL,
  raw_status_text TEXT NULL,
  raw_snippet TEXT NULL,
  raw_response_json JSON NULL,
  first_seen_product_id VARCHAR(64) NULL,
  first_seen_sort_date DATETIME NULL,
  error_message TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_store_checked (store_id, checked_at),
  INDEX idx_status_checked (status, checked_at),
  INDEX idx_store_seq_checked (store_seq, checked_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS fraud_store_activity_snapshots (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  store_id VARCHAR(64) NOT NULL,
  store_seq BIGINT NULL,
  checked_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  observed_at DATETIME NULL,
  posts_last_1h INT NOT NULL DEFAULT 0,
  posts_last_6h INT NOT NULL DEFAULT 0,
  posts_last_24h INT NOT NULL DEFAULT 0,
  posts_last_7d INT NOT NULL DEFAULT 0,
  visible_product_count INT NULL,
  store_name VARCHAR(255) NULL,
  store_name_fingerprint CHAR(64) NULL,
  profile_fingerprint CHAR(64) NULL,
  profile_image_url TEXT NULL,
  has_default_profile_image TINYINT NULL,
  store_level VARCHAR(100) NULL,
  store_level_number INT NULL,
  review_count INT NULL,
  reliability_score INT NULL,
  activity_score INT NULL,
  notified_score INT NULL,
  safe_trade_count INT NULL,
  trust_score INT NULL,
  chat_response_ratio VARCHAR(50) NULL,
  chat_response_time INT NULL,
  chat_response_time_text VARCHAR(100) NULL,
  visit_today_count INT NULL,
  visit_total_count INT NULL,
  store_grade DECIMAL(10,2) NULL,
  user_type INT NULL,
  partner_center_seller_yn TINYINT NULL,
  is_official_account TINYINT NULL,
  store_desc TEXT NULL,
  store_desc_length INT NULL,
  raw_json JSON NULL,
  first_seen_product_id VARCHAR(64) NULL,
  first_seen_sort_date DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_store_checked (store_id, checked_at),
  INDEX idx_checked_at (checked_at),
  INDEX idx_store_seq_observed (store_seq, observed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS fraud_training_label_candidates (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  product_id VARCHAR(64) NOT NULL,
  store_id VARCHAR(64) NOT NULL,
  listing_sort_date DATETIME NOT NULL,
  discovered_at DATETIME NULL,
  first_inactive_at DATETIME NULL,
  inactive_after_minutes INT NULL,
  label TINYINT NULL,
  label_reason VARCHAR(255) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_product_id (product_id),
  INDEX idx_store_id (store_id),
  INDEX idx_label (label),
  INDEX idx_listing_sort_date (listing_sort_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS joongna_store_name_changes (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  store_seq BIGINT NOT NULL,
  old_name VARCHAR(255) NULL,
  new_name VARCHAR(255) NOT NULL,
  old_fingerprint CHAR(64) NULL,
  new_fingerprint CHAR(64) NOT NULL,
  changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  source VARCHAR(50) NOT NULL DEFAULT 'my_store_api',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_store_name_changes_store_seq (store_seq),
  KEY idx_store_name_changes_changed_at (changed_at),
  KEY idx_store_name_changes_new_fingerprint (new_fingerprint)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET @target_db = DATABASE();

SET @schema_table = 'fraud_store_status_snapshots';
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'store_seq';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_status_snapshots ADD COLUMN store_seq BIGINT NULL AFTER store_id', 'SELECT "fraud_store_status_snapshots.store_seq exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'status_reason';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_status_snapshots ADD COLUMN status_reason VARCHAR(100) NULL AFTER status', 'SELECT "fraud_store_status_snapshots.status_reason exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'source';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_status_snapshots ADD COLUMN source VARCHAR(50) NULL AFTER status_reason', 'SELECT "fraud_store_status_snapshots.source exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'http_status';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_status_snapshots ADD COLUMN http_status INT NULL AFTER is_active', 'SELECT "fraud_store_status_snapshots.http_status exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'meta_code';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_status_snapshots ADD COLUMN meta_code INT NULL AFTER http_status', 'SELECT "fraud_store_status_snapshots.meta_code exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'meta_message';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_status_snapshots ADD COLUMN meta_message VARCHAR(255) NULL AFTER meta_code', 'SELECT "fraud_store_status_snapshots.meta_message exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'raw_snippet';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_status_snapshots ADD COLUMN raw_snippet TEXT NULL AFTER raw_status_text', 'SELECT "fraud_store_status_snapshots.raw_snippet exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_idx FROM INFORMATION_SCHEMA.STATISTICS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND INDEX_NAME = 'idx_store_seq_checked';
SET @sql = IF(@has_idx = 0, 'ALTER TABLE fraud_store_status_snapshots ADD INDEX idx_store_seq_checked (store_seq, checked_at)', 'SELECT "idx_store_seq_checked exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @schema_table = 'fraud_store_activity_snapshots';
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'store_seq';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN store_seq BIGINT NULL AFTER store_id', 'SELECT "fraud_store_activity_snapshots.store_seq exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'observed_at';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN observed_at DATETIME NULL AFTER checked_at', 'SELECT "fraud_store_activity_snapshots.observed_at exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'store_name';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN store_name VARCHAR(255) NULL AFTER visible_product_count', 'SELECT "fraud_store_activity_snapshots.store_name exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'store_name_fingerprint';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN store_name_fingerprint CHAR(64) NULL AFTER store_name', 'SELECT "fraud_store_activity_snapshots.store_name_fingerprint exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'profile_fingerprint';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN profile_fingerprint CHAR(64) NULL AFTER store_name_fingerprint', 'SELECT "fraud_store_activity_snapshots.profile_fingerprint exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'profile_image_url';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN profile_image_url TEXT NULL AFTER profile_fingerprint', 'SELECT "fraud_store_activity_snapshots.profile_image_url exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'has_default_profile_image';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN has_default_profile_image TINYINT NULL AFTER profile_image_url', 'SELECT "fraud_store_activity_snapshots.has_default_profile_image exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'store_level';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN store_level VARCHAR(100) NULL AFTER has_default_profile_image', 'SELECT "fraud_store_activity_snapshots.store_level exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'store_level_number';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN store_level_number INT NULL AFTER store_level', 'SELECT "fraud_store_activity_snapshots.store_level_number exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'review_count';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN review_count INT NULL AFTER store_level_number', 'SELECT "fraud_store_activity_snapshots.review_count exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'reliability_score';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN reliability_score INT NULL AFTER review_count', 'SELECT "fraud_store_activity_snapshots.reliability_score exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'activity_score';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN activity_score INT NULL AFTER reliability_score', 'SELECT "fraud_store_activity_snapshots.activity_score exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'notified_score';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN notified_score INT NULL AFTER activity_score', 'SELECT "fraud_store_activity_snapshots.notified_score exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'safe_trade_count';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN safe_trade_count INT NULL AFTER notified_score', 'SELECT "fraud_store_activity_snapshots.safe_trade_count exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'trust_score';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN trust_score INT NULL AFTER safe_trade_count', 'SELECT "fraud_store_activity_snapshots.trust_score exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'chat_response_ratio';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN chat_response_ratio VARCHAR(50) NULL AFTER trust_score', 'SELECT "fraud_store_activity_snapshots.chat_response_ratio exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'chat_response_time';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN chat_response_time INT NULL AFTER chat_response_ratio', 'SELECT "fraud_store_activity_snapshots.chat_response_time exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'chat_response_time_text';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN chat_response_time_text VARCHAR(100) NULL AFTER chat_response_time', 'SELECT "fraud_store_activity_snapshots.chat_response_time_text exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'visit_today_count';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN visit_today_count INT NULL AFTER chat_response_time_text', 'SELECT "fraud_store_activity_snapshots.visit_today_count exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'visit_total_count';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN visit_total_count INT NULL AFTER visit_today_count', 'SELECT "fraud_store_activity_snapshots.visit_total_count exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'store_grade';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN store_grade DECIMAL(10,2) NULL AFTER visit_total_count', 'SELECT "fraud_store_activity_snapshots.store_grade exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'user_type';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN user_type INT NULL AFTER store_grade', 'SELECT "fraud_store_activity_snapshots.user_type exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'partner_center_seller_yn';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN partner_center_seller_yn TINYINT NULL AFTER user_type', 'SELECT "fraud_store_activity_snapshots.partner_center_seller_yn exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'is_official_account';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN is_official_account TINYINT NULL AFTER partner_center_seller_yn', 'SELECT "fraud_store_activity_snapshots.is_official_account exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'store_desc';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN store_desc TEXT NULL AFTER is_official_account', 'SELECT "fraud_store_activity_snapshots.store_desc exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'store_desc_length';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN store_desc_length INT NULL AFTER store_desc', 'SELECT "fraud_store_activity_snapshots.store_desc_length exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'raw_json';
SET @sql = IF(@has_col = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD COLUMN raw_json JSON NULL AFTER store_desc_length', 'SELECT "fraud_store_activity_snapshots.raw_json exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_idx FROM INFORMATION_SCHEMA.STATISTICS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND INDEX_NAME = 'idx_store_seq_observed';
SET @sql = IF(@has_idx = 0, 'ALTER TABLE fraud_store_activity_snapshots ADD INDEX idx_store_seq_observed (store_seq, observed_at)', 'SELECT "idx_store_seq_observed exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @schema_table = 'joongna_store_profiles';
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'store_name_fingerprint';
SET @sql = IF(@has_col = 0, 'ALTER TABLE joongna_store_profiles ADD COLUMN store_name_fingerprint CHAR(64) NULL AFTER store_name', 'SELECT "joongna_store_profiles.store_name_fingerprint exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'profile_fingerprint';
SET @sql = IF(@has_col = 0, 'ALTER TABLE joongna_store_profiles ADD COLUMN profile_fingerprint CHAR(64) NULL AFTER store_name_fingerprint', 'SELECT "joongna_store_profiles.profile_fingerprint exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'profile_image_url';
SET @sql = IF(@has_col = 0, 'ALTER TABLE joongna_store_profiles ADD COLUMN profile_image_url TEXT NULL AFTER profile_fingerprint', 'SELECT "joongna_store_profiles.profile_image_url exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'store_level';
SET @sql = IF(@has_col = 0, 'ALTER TABLE joongna_store_profiles ADD COLUMN store_level VARCHAR(100) NULL AFTER profile_image_url', 'SELECT "joongna_store_profiles.store_level exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'store_level_number';
SET @sql = IF(@has_col = 0, 'ALTER TABLE joongna_store_profiles ADD COLUMN store_level_number INT NULL AFTER store_level', 'SELECT "joongna_store_profiles.store_level_number exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'review_count';
SET @sql = IF(@has_col = 0, 'ALTER TABLE joongna_store_profiles ADD COLUMN review_count INT NULL AFTER store_level_number', 'SELECT "joongna_store_profiles.review_count exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'reliability_score';
SET @sql = IF(@has_col = 0, 'ALTER TABLE joongna_store_profiles ADD COLUMN reliability_score INT NULL AFTER review_count', 'SELECT "joongna_store_profiles.reliability_score exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'activity_score';
SET @sql = IF(@has_col = 0, 'ALTER TABLE joongna_store_profiles ADD COLUMN activity_score INT NULL AFTER reliability_score', 'SELECT "joongna_store_profiles.activity_score exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'notified_score';
SET @sql = IF(@has_col = 0, 'ALTER TABLE joongna_store_profiles ADD COLUMN notified_score INT NULL AFTER activity_score', 'SELECT "joongna_store_profiles.notified_score exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'safe_trade_count';
SET @sql = IF(@has_col = 0, 'ALTER TABLE joongna_store_profiles ADD COLUMN safe_trade_count INT NULL AFTER notified_score', 'SELECT "joongna_store_profiles.safe_trade_count exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'trust_score';
SET @sql = IF(@has_col = 0, 'ALTER TABLE joongna_store_profiles ADD COLUMN trust_score INT NULL AFTER safe_trade_count', 'SELECT "joongna_store_profiles.trust_score exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'chat_response_ratio';
SET @sql = IF(@has_col = 0, 'ALTER TABLE joongna_store_profiles ADD COLUMN chat_response_ratio VARCHAR(50) NULL AFTER trust_score', 'SELECT "joongna_store_profiles.chat_response_ratio exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'chat_response_time';
SET @sql = IF(@has_col = 0, 'ALTER TABLE joongna_store_profiles ADD COLUMN chat_response_time INT NULL AFTER chat_response_ratio', 'SELECT "joongna_store_profiles.chat_response_time exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'chat_response_time_text';
SET @sql = IF(@has_col = 0, 'ALTER TABLE joongna_store_profiles ADD COLUMN chat_response_time_text VARCHAR(100) NULL AFTER chat_response_time', 'SELECT "joongna_store_profiles.chat_response_time_text exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'visit_today_count';
SET @sql = IF(@has_col = 0, 'ALTER TABLE joongna_store_profiles ADD COLUMN visit_today_count INT NULL AFTER chat_response_time_text', 'SELECT "joongna_store_profiles.visit_today_count exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'visit_total_count';
SET @sql = IF(@has_col = 0, 'ALTER TABLE joongna_store_profiles ADD COLUMN visit_total_count INT NULL AFTER visit_today_count', 'SELECT "joongna_store_profiles.visit_total_count exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'store_grade';
SET @sql = IF(@has_col = 0, 'ALTER TABLE joongna_store_profiles ADD COLUMN store_grade DECIMAL(10,2) NULL AFTER visit_total_count', 'SELECT "joongna_store_profiles.store_grade exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'user_type';
SET @sql = IF(@has_col = 0, 'ALTER TABLE joongna_store_profiles ADD COLUMN user_type INT NULL AFTER store_grade', 'SELECT "joongna_store_profiles.user_type exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'partner_center_seller_yn';
SET @sql = IF(@has_col = 0, 'ALTER TABLE joongna_store_profiles ADD COLUMN partner_center_seller_yn TINYINT NULL AFTER user_type', 'SELECT "joongna_store_profiles.partner_center_seller_yn exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'is_official_account';
SET @sql = IF(@has_col = 0, 'ALTER TABLE joongna_store_profiles ADD COLUMN is_official_account TINYINT NULL AFTER partner_center_seller_yn', 'SELECT "joongna_store_profiles.is_official_account exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'store_desc';
SET @sql = IF(@has_col = 0, 'ALTER TABLE joongna_store_profiles ADD COLUMN store_desc TEXT NULL AFTER is_official_account', 'SELECT "joongna_store_profiles.store_desc exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'last_status';
SET @sql = IF(@has_col = 0, 'ALTER TABLE joongna_store_profiles ADD COLUMN last_status VARCHAR(50) NULL AFTER store_desc', 'SELECT "joongna_store_profiles.last_status exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'last_status_reason';
SET @sql = IF(@has_col = 0, 'ALTER TABLE joongna_store_profiles ADD COLUMN last_status_reason VARCHAR(100) NULL AFTER last_status', 'SELECT "joongna_store_profiles.last_status_reason exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'last_status_checked_at';
SET @sql = IF(@has_col = 0, 'ALTER TABLE joongna_store_profiles ADD COLUMN last_status_checked_at DATETIME NULL AFTER last_status_reason', 'SELECT "joongna_store_profiles.last_status_checked_at exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
SELECT COUNT(*) INTO @has_col FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = @schema_table AND COLUMN_NAME = 'last_seen_at';
SET @sql = IF(@has_col = 0, 'ALTER TABLE joongna_store_profiles ADD COLUMN last_seen_at DATETIME NULL AFTER last_status_checked_at', 'SELECT "joongna_store_profiles.last_seen_at exists"');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
