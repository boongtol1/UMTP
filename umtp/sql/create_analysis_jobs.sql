USE UMTP_RB;

CREATE TABLE IF NOT EXISTS analysis_jobs (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  source VARCHAR(50) NOT NULL DEFAULT 'joongna',
  product_id VARCHAR(100) NULL,
  url TEXT NOT NULL,
  title VARCHAR(500) NULL,
  price_krw INT NULL,
  search_keyword VARCHAR(255) NULL,
  user_id VARCHAR(100) NULL,
  watch_rule_id BIGINT UNSIGNED NULL,
  sort_date DATETIME NULL,
  trigger_reason VARCHAR(100) NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'pending',
  error_message TEXT NULL,
  attempts INT NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  started_at TIMESTAMP NULL,
  processed_at TIMESTAMP NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_analysis_jobs_status (status),
  KEY idx_analysis_jobs_created_at (created_at),
  KEY idx_analysis_jobs_watch_rule (watch_rule_id),
  KEY idx_analysis_jobs_product (product_id),
  KEY idx_analysis_jobs_sort_date (sort_date),
  UNIQUE KEY uq_analysis_jobs_user_rule_product (user_id, watch_rule_id, product_id, sort_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_watch_rule_id
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'analysis_jobs'
  AND COLUMN_NAME = 'watch_rule_id';
SET @sql_watch_rule_id = IF(
  @has_watch_rule_id = 0,
  'ALTER TABLE analysis_jobs ADD COLUMN watch_rule_id BIGINT UNSIGNED NULL AFTER user_id',
  'SELECT "watch_rule_id exists"'
);
PREPARE stmt_watch_rule_id FROM @sql_watch_rule_id;
EXECUTE stmt_watch_rule_id;
DEALLOCATE PREPARE stmt_watch_rule_id;

SELECT COUNT(*) INTO @has_sort_date
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'analysis_jobs'
  AND COLUMN_NAME = 'sort_date';
SET @sql_sort_date = IF(
  @has_sort_date = 0,
  'ALTER TABLE analysis_jobs ADD COLUMN sort_date DATETIME NULL AFTER watch_rule_id',
  'SELECT "sort_date exists"'
);
PREPARE stmt_sort_date FROM @sql_sort_date;
EXECUTE stmt_sort_date;
DEALLOCATE PREPARE stmt_sort_date;

SELECT COUNT(*) INTO @has_idx_sort_date
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'analysis_jobs'
  AND INDEX_NAME = 'idx_analysis_jobs_sort_date';
SET @sql_idx_sort_date = IF(
  @has_idx_sort_date = 0,
  'ALTER TABLE analysis_jobs ADD INDEX idx_analysis_jobs_sort_date (sort_date)',
  'SELECT "idx_analysis_jobs_sort_date exists"'
);
PREPARE stmt_idx_sort_date FROM @sql_idx_sort_date;
EXECUTE stmt_idx_sort_date;
DEALLOCATE PREPARE stmt_idx_sort_date;

SELECT COUNT(*) INTO @has_uq_analysis_user_product
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'analysis_jobs'
  AND INDEX_NAME = 'uq_analysis_jobs_user_product';
SET @sql_drop_uq_analysis_user_product = IF(
  @has_uq_analysis_user_product = 0,
  'SELECT "uq_analysis_jobs_user_product already absent"',
  'ALTER TABLE analysis_jobs DROP INDEX uq_analysis_jobs_user_product'
);
PREPARE stmt_drop_uq_analysis_user_product FROM @sql_drop_uq_analysis_user_product;
EXECUTE stmt_drop_uq_analysis_user_product;
DEALLOCATE PREPARE stmt_drop_uq_analysis_user_product;

SELECT COUNT(*) INTO @has_uq_analysis_user_rule_product
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'analysis_jobs'
  AND INDEX_NAME = 'uq_analysis_jobs_user_rule_product';

SELECT GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX SEPARATOR ',')
INTO @uq_analysis_user_rule_product_cols
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'analysis_jobs'
  AND INDEX_NAME = 'uq_analysis_jobs_user_rule_product';

SET @sql_drop_uq_analysis_user_rule_product_mismatch = IF(
  @has_uq_analysis_user_rule_product = 1
  AND IFNULL(@uq_analysis_user_rule_product_cols, '') <> 'user_id,watch_rule_id,product_id,sort_date',
  'ALTER TABLE analysis_jobs DROP INDEX uq_analysis_jobs_user_rule_product',
  'SELECT "uq_analysis_jobs_user_rule_product definition ok"'
);
PREPARE stmt_drop_uq_analysis_user_rule_product_mismatch FROM @sql_drop_uq_analysis_user_rule_product_mismatch;
EXECUTE stmt_drop_uq_analysis_user_rule_product_mismatch;
DEALLOCATE PREPARE stmt_drop_uq_analysis_user_rule_product_mismatch;

SELECT COUNT(*) INTO @has_uq_analysis_user_rule_product_after_drop
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'analysis_jobs'
  AND INDEX_NAME = 'uq_analysis_jobs_user_rule_product';
SET @sql_uq_analysis_user_rule_product = IF(
  @has_uq_analysis_user_rule_product_after_drop = 0,
  'ALTER TABLE analysis_jobs ADD UNIQUE KEY uq_analysis_jobs_user_rule_product (user_id, watch_rule_id, product_id, sort_date)',
  'SELECT "uq_analysis_jobs_user_rule_product exists"'
);
PREPARE stmt_uq_analysis_user_rule_product FROM @sql_uq_analysis_user_rule_product;
EXECUTE stmt_uq_analysis_user_rule_product;
DEALLOCATE PREPARE stmt_uq_analysis_user_rule_product;
