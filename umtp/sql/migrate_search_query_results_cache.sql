USE UMTP_RB;

CREATE TABLE IF NOT EXISTS search_queries (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  source VARCHAR(50) NOT NULL,
  normalized_keyword VARCHAR(255) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_polled_at DATETIME NULL,
  last_status VARCHAR(30) NOT NULL DEFAULT 'ok',
  UNIQUE KEY uq_search_queries_source_keyword (source, normalized_keyword),
  KEY idx_search_queries_last_polled_at (last_polled_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS search_results (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  search_query_id BIGINT UNSIGNED NOT NULL,
  product_id VARCHAR(100) NOT NULL,
  title VARCHAR(500) NULL,
  price INT NULL,
  sort_date DATETIME NULL,
  url TEXT NULL,
  seller_store_seq BIGINT NULL,
  seller_store_name VARCHAR(100) NULL,
  seller_profile_image_url TEXT NULL,
  seller_store_level VARCHAR(50) NULL,
  seller_trust_score INT NULL,
  seller_review_count INT NULL,
  raw_json LONGTEXT NULL,
  fetched_at DATETIME NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_search_results_query_fetched (search_query_id, fetched_at),
  KEY idx_search_results_product (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_search_results_seller_store_seq
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'search_results'
  AND COLUMN_NAME = 'seller_store_seq';
SET @sql_search_results_seller_store_seq = IF(
  @has_search_results_seller_store_seq = 0,
  'ALTER TABLE search_results ADD COLUMN seller_store_seq BIGINT NULL AFTER url',
  'SELECT "search_results.seller_store_seq exists"'
);
PREPARE stmt_search_results_seller_store_seq FROM @sql_search_results_seller_store_seq;
EXECUTE stmt_search_results_seller_store_seq;
DEALLOCATE PREPARE stmt_search_results_seller_store_seq;

SELECT COUNT(*) INTO @has_search_results_seller_store_name
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'search_results'
  AND COLUMN_NAME = 'seller_store_name';
SET @sql_search_results_seller_store_name = IF(
  @has_search_results_seller_store_name = 0,
  'ALTER TABLE search_results ADD COLUMN seller_store_name VARCHAR(100) NULL AFTER seller_store_seq',
  'SELECT "search_results.seller_store_name exists"'
);
PREPARE stmt_search_results_seller_store_name FROM @sql_search_results_seller_store_name;
EXECUTE stmt_search_results_seller_store_name;
DEALLOCATE PREPARE stmt_search_results_seller_store_name;

SELECT COUNT(*) INTO @has_search_results_seller_profile_image_url
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'search_results'
  AND COLUMN_NAME = 'seller_profile_image_url';
SET @sql_search_results_seller_profile_image_url = IF(
  @has_search_results_seller_profile_image_url = 0,
  'ALTER TABLE search_results ADD COLUMN seller_profile_image_url TEXT NULL AFTER seller_store_name',
  'SELECT "search_results.seller_profile_image_url exists"'
);
PREPARE stmt_search_results_seller_profile_image_url FROM @sql_search_results_seller_profile_image_url;
EXECUTE stmt_search_results_seller_profile_image_url;
DEALLOCATE PREPARE stmt_search_results_seller_profile_image_url;

SELECT COUNT(*) INTO @has_search_results_seller_store_level
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'search_results'
  AND COLUMN_NAME = 'seller_store_level';
SET @sql_search_results_seller_store_level = IF(
  @has_search_results_seller_store_level = 0,
  'ALTER TABLE search_results ADD COLUMN seller_store_level VARCHAR(50) NULL AFTER seller_profile_image_url',
  'SELECT "search_results.seller_store_level exists"'
);
PREPARE stmt_search_results_seller_store_level FROM @sql_search_results_seller_store_level;
EXECUTE stmt_search_results_seller_store_level;
DEALLOCATE PREPARE stmt_search_results_seller_store_level;

SELECT COUNT(*) INTO @has_search_results_seller_trust_score
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'search_results'
  AND COLUMN_NAME = 'seller_trust_score';
SET @sql_search_results_seller_trust_score = IF(
  @has_search_results_seller_trust_score = 0,
  'ALTER TABLE search_results ADD COLUMN seller_trust_score INT NULL AFTER seller_store_level',
  'SELECT "search_results.seller_trust_score exists"'
);
PREPARE stmt_search_results_seller_trust_score FROM @sql_search_results_seller_trust_score;
EXECUTE stmt_search_results_seller_trust_score;
DEALLOCATE PREPARE stmt_search_results_seller_trust_score;

SELECT COUNT(*) INTO @has_search_results_seller_review_count
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'search_results'
  AND COLUMN_NAME = 'seller_review_count';
SET @sql_search_results_seller_review_count = IF(
  @has_search_results_seller_review_count = 0,
  'ALTER TABLE search_results ADD COLUMN seller_review_count INT NULL AFTER seller_trust_score',
  'SELECT "search_results.seller_review_count exists"'
);
PREPARE stmt_search_results_seller_review_count FROM @sql_search_results_seller_review_count;
EXECUTE stmt_search_results_seller_review_count;
DEALLOCATE PREPARE stmt_search_results_seller_review_count;
