USE UMTP_RB;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_first_seen_at
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_seen_products'
  AND COLUMN_NAME = 'first_seen_at';
SET @sql_first_seen_at = IF(
  @has_first_seen_at = 0,
  'ALTER TABLE joongna_seen_products ADD COLUMN first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP',
  'SELECT "first_seen_at already exists"'
);
PREPARE stmt_first_seen_at FROM @sql_first_seen_at;
EXECUTE stmt_first_seen_at;
DEALLOCATE PREPARE stmt_first_seen_at;

SELECT COUNT(*) INTO @has_last_seen_at
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_seen_products'
  AND COLUMN_NAME = 'last_seen_at';
SET @sql_last_seen_at = IF(
  @has_last_seen_at = 0,
  'ALTER TABLE joongna_seen_products ADD COLUMN last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP AFTER first_seen_at',
  'SELECT "last_seen_at already exists"'
);
PREPARE stmt_last_seen_at FROM @sql_last_seen_at;
EXECUTE stmt_last_seen_at;
DEALLOCATE PREPARE stmt_last_seen_at;

SELECT COUNT(*) INTO @has_last_analyzed_at
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_seen_products'
  AND COLUMN_NAME = 'last_analyzed_at';
SET @sql_last_analyzed_at = IF(
  @has_last_analyzed_at = 0,
  'ALTER TABLE joongna_seen_products ADD COLUMN last_analyzed_at TIMESTAMP NULL AFTER last_seen_at',
  'SELECT "last_analyzed_at already exists"'
);
PREPARE stmt_last_analyzed_at FROM @sql_last_analyzed_at;
EXECUTE stmt_last_analyzed_at;
DEALLOCATE PREPARE stmt_last_analyzed_at;

SELECT COUNT(*) INTO @has_seen_count
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_seen_products'
  AND COLUMN_NAME = 'seen_count';
SET @sql_seen_count = IF(
  @has_seen_count = 0,
  'ALTER TABLE joongna_seen_products ADD COLUMN seen_count INT NOT NULL DEFAULT 1 AFTER last_analyzed_at',
  'SELECT "seen_count already exists"'
);
PREPARE stmt_seen_count FROM @sql_seen_count;
EXECUTE stmt_seen_count;
DEALLOCATE PREPARE stmt_seen_count;

SELECT COUNT(*) INTO @has_last_title
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_seen_products'
  AND COLUMN_NAME = 'last_title';
SET @sql_last_title = IF(
  @has_last_title = 0,
  'ALTER TABLE joongna_seen_products ADD COLUMN last_title VARCHAR(500) NULL AFTER seen_count',
  'SELECT "last_title already exists"'
);
PREPARE stmt_last_title FROM @sql_last_title;
EXECUTE stmt_last_title;
DEALLOCATE PREPARE stmt_last_title;

SELECT COUNT(*) INTO @has_last_price_krw
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_seen_products'
  AND COLUMN_NAME = 'last_price_krw';
SET @sql_last_price_krw = IF(
  @has_last_price_krw = 0,
  'ALTER TABLE joongna_seen_products ADD COLUMN last_price_krw INT NULL AFTER last_title',
  'SELECT "last_price_krw already exists"'
);
PREPARE stmt_last_price_krw FROM @sql_last_price_krw;
EXECUTE stmt_last_price_krw;
DEALLOCATE PREPARE stmt_last_price_krw;

SELECT COUNT(*) INTO @has_last_status
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_seen_products'
  AND COLUMN_NAME = 'last_status';
SET @sql_last_status = IF(
  @has_last_status = 0,
  'ALTER TABLE joongna_seen_products ADD COLUMN last_status VARCHAR(50) NULL AFTER last_price_krw',
  'SELECT "last_status already exists"'
);
PREPARE stmt_last_status FROM @sql_last_status;
EXECUTE stmt_last_status;
DEALLOCATE PREPARE stmt_last_status;

SELECT COUNT(*) INTO @has_last_refresh_key
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_seen_products'
  AND COLUMN_NAME = 'last_refresh_key';
SET @sql_last_refresh_key = IF(
  @has_last_refresh_key = 0,
  'ALTER TABLE joongna_seen_products ADD COLUMN last_refresh_key VARCHAR(255) NULL AFTER last_status',
  'SELECT "last_refresh_key already exists"'
);
PREPARE stmt_last_refresh_key FROM @sql_last_refresh_key;
EXECUTE stmt_last_refresh_key;
DEALLOCATE PREPARE stmt_last_refresh_key;

SELECT COUNT(*) INTO @has_last_change_reason
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_seen_products'
  AND COLUMN_NAME = 'last_change_reason';
SET @sql_last_change_reason = IF(
  @has_last_change_reason = 0,
  'ALTER TABLE joongna_seen_products ADD COLUMN last_change_reason VARCHAR(255) NULL AFTER last_refresh_key',
  'SELECT "last_change_reason already exists"'
);
PREPARE stmt_last_change_reason FROM @sql_last_change_reason;
EXECUTE stmt_last_change_reason;
DEALLOCATE PREPARE stmt_last_change_reason;

SELECT COUNT(*) INTO @has_last_body_hash
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_seen_products'
  AND COLUMN_NAME = 'last_body_hash';
SET @sql_last_body_hash = IF(
  @has_last_body_hash = 0,
  'ALTER TABLE joongna_seen_products ADD COLUMN last_body_hash VARCHAR(64) NULL AFTER last_change_reason',
  'SELECT "last_body_hash already exists"'
);
PREPARE stmt_last_body_hash FROM @sql_last_body_hash;
EXECUTE stmt_last_body_hash;
DEALLOCATE PREPARE stmt_last_body_hash;

SELECT COUNT(*) INTO @has_last_self_check_hash
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_seen_products'
  AND COLUMN_NAME = 'last_self_check_hash';
SET @sql_last_self_check_hash = IF(
  @has_last_self_check_hash = 0,
  'ALTER TABLE joongna_seen_products ADD COLUMN last_self_check_hash VARCHAR(64) NULL AFTER last_body_hash',
  'SELECT "last_self_check_hash already exists"'
);
PREPARE stmt_last_self_check_hash FROM @sql_last_self_check_hash;
EXECUTE stmt_last_self_check_hash;
DEALLOCATE PREPARE stmt_last_self_check_hash;

SELECT COUNT(*) INTO @has_last_content_revision_hash
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_seen_products'
  AND COLUMN_NAME = 'last_content_revision_hash';
SET @sql_last_content_revision_hash = IF(
  @has_last_content_revision_hash = 0,
  'ALTER TABLE joongna_seen_products ADD COLUMN last_content_revision_hash VARCHAR(64) NULL AFTER last_self_check_hash',
  'SELECT "last_content_revision_hash already exists"'
);
PREPARE stmt_last_content_revision_hash FROM @sql_last_content_revision_hash;
EXECUTE stmt_last_content_revision_hash;
DEALLOCATE PREPARE stmt_last_content_revision_hash;

SELECT COUNT(*) INTO @has_last_content_checked_at
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_seen_products'
  AND COLUMN_NAME = 'last_content_checked_at';
SET @sql_last_content_checked_at = IF(
  @has_last_content_checked_at = 0,
  'ALTER TABLE joongna_seen_products ADD COLUMN last_content_checked_at TIMESTAMP NULL AFTER last_content_revision_hash',
  'SELECT "last_content_checked_at already exists"'
);
PREPARE stmt_last_content_checked_at FROM @sql_last_content_checked_at;
EXECUTE stmt_last_content_checked_at;
DEALLOCATE PREPARE stmt_last_content_checked_at;

SELECT COUNT(*) INTO @has_updated_at
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_seen_products'
  AND COLUMN_NAME = 'updated_at';
SET @sql_updated_at = IF(
  @has_updated_at = 0,
  'ALTER TABLE joongna_seen_products ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER last_change_reason',
  'SELECT "updated_at already exists"'
);
PREPARE stmt_updated_at FROM @sql_updated_at;
EXECUTE stmt_updated_at;
DEALLOCATE PREPARE stmt_updated_at;
