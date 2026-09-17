USE UMTP_RB;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_body_hash
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'search_results' AND COLUMN_NAME = 'body_hash';
SET @sql_body_hash = IF(
  @has_body_hash = 0,
  'ALTER TABLE search_results ADD COLUMN body_hash VARCHAR(64) NULL AFTER body_text',
  'SELECT "search_results.body_hash exists"'
);
PREPARE stmt_body_hash FROM @sql_body_hash;
EXECUTE stmt_body_hash;
DEALLOCATE PREPARE stmt_body_hash;

SELECT COUNT(*) INTO @has_body_fetched_at
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'search_results' AND COLUMN_NAME = 'body_fetched_at';
SET @sql_body_fetched_at = IF(
  @has_body_fetched_at = 0,
  'ALTER TABLE search_results ADD COLUMN body_fetched_at TIMESTAMP NULL AFTER body_hash',
  'SELECT "search_results.body_fetched_at exists"'
);
PREPARE stmt_body_fetched_at FROM @sql_body_fetched_at;
EXECUTE stmt_body_fetched_at;
DEALLOCATE PREPARE stmt_body_fetched_at;

SELECT COUNT(*) INTO @has_self_check_json
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'search_results' AND COLUMN_NAME = 'self_check_json';
SET @sql_self_check_json = IF(
  @has_self_check_json = 0,
  'ALTER TABLE search_results ADD COLUMN self_check_json JSON NULL AFTER body_fetched_at',
  'SELECT "search_results.self_check_json exists"'
);
PREPARE stmt_self_check_json FROM @sql_self_check_json;
EXECUTE stmt_self_check_json;
DEALLOCATE PREPARE stmt_self_check_json;

SELECT COUNT(*) INTO @has_profile_image_url
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'joongna_store_profiles' AND COLUMN_NAME = 'profile_image_url';
SET @sql_profile_image_url = IF(
  @has_profile_image_url = 0,
  'ALTER TABLE joongna_store_profiles ADD COLUMN profile_image_url TEXT NULL AFTER store_name',
  'SELECT "joongna_store_profiles.profile_image_url exists"'
);
PREPARE stmt_profile_image_url FROM @sql_profile_image_url;
EXECUTE stmt_profile_image_url;
DEALLOCATE PREPARE stmt_profile_image_url;

SELECT COUNT(*) INTO @has_store_level
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'joongna_store_profiles' AND COLUMN_NAME = 'store_level';
SET @sql_store_level = IF(
  @has_store_level = 0,
  'ALTER TABLE joongna_store_profiles ADD COLUMN store_level VARCHAR(50) NULL AFTER profile_image_url',
  'SELECT "joongna_store_profiles.store_level exists"'
);
PREPARE stmt_store_level FROM @sql_store_level;
EXECUTE stmt_store_level;
DEALLOCATE PREPARE stmt_store_level;

SELECT COUNT(*) INTO @has_trust_score
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'joongna_store_profiles' AND COLUMN_NAME = 'trust_score';
SET @sql_trust_score = IF(
  @has_trust_score = 0,
  'ALTER TABLE joongna_store_profiles ADD COLUMN trust_score INT NULL AFTER store_level',
  'SELECT "joongna_store_profiles.trust_score exists"'
);
PREPARE stmt_trust_score FROM @sql_trust_score;
EXECUTE stmt_trust_score;
DEALLOCATE PREPARE stmt_trust_score;

SELECT COUNT(*) INTO @has_review_count
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db AND TABLE_NAME = 'joongna_store_profiles' AND COLUMN_NAME = 'review_count';
SET @sql_review_count = IF(
  @has_review_count = 0,
  'ALTER TABLE joongna_store_profiles ADD COLUMN review_count INT NULL AFTER trust_score',
  'SELECT "joongna_store_profiles.review_count exists"'
);
PREPARE stmt_review_count FROM @sql_review_count;
EXECUTE stmt_review_count;
DEALLOCATE PREPARE stmt_review_count;

SELECT COUNT(*) INTO @has_content_check_index
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_seen_products'
  AND INDEX_NAME = 'idx_seen_content_refresh';
SET @sql_content_check_index = IF(
  @has_content_check_index = 0,
  'ALTER TABLE joongna_seen_products ADD INDEX idx_seen_content_refresh (last_content_checked_at, last_seen_at)',
  'SELECT "idx_seen_content_refresh exists"'
);
PREPARE stmt_content_check_index FROM @sql_content_check_index;
EXECUTE stmt_content_check_index;
DEALLOCATE PREPARE stmt_content_check_index;
