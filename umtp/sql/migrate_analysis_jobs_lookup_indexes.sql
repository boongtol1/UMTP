USE UMTP_RB;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_analysis_jobs_table
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'analysis_jobs';

SELECT COUNT(*) INTO @has_idx_user_source_keyword_created_at_name
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'analysis_jobs'
  AND INDEX_NAME = 'idx_analysis_jobs_user_source_keyword_created_at';

SELECT COUNT(*) INTO @has_idx_user_source_keyword_created_at_equivalent
FROM (
  SELECT INDEX_NAME
  FROM INFORMATION_SCHEMA.STATISTICS
  WHERE TABLE_SCHEMA = @target_db
    AND TABLE_NAME = 'analysis_jobs'
  GROUP BY INDEX_NAME
  HAVING GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX SEPARATOR ',') = 'user_id,source,search_keyword,created_at'
) AS t;

SET @sql_add_idx_user_source_keyword_created_at = IF(
  @has_analysis_jobs_table = 0,
  'SELECT ''skip add idx_analysis_jobs_user_source_keyword_created_at (analysis_jobs missing)''',
  IF(
    @has_idx_user_source_keyword_created_at_name > 0 OR @has_idx_user_source_keyword_created_at_equivalent > 0,
    'SELECT ''idx_analysis_jobs_user_source_keyword_created_at already exists or equivalent exists''',
    'ALTER TABLE analysis_jobs ADD INDEX idx_analysis_jobs_user_source_keyword_created_at (user_id, source, search_keyword, created_at)'
  )
);
PREPARE stmt_add_idx_user_source_keyword_created_at FROM @sql_add_idx_user_source_keyword_created_at;
EXECUTE stmt_add_idx_user_source_keyword_created_at;
DEALLOCATE PREPARE stmt_add_idx_user_source_keyword_created_at;

SELECT COUNT(*) INTO @has_idx_user_source_keyword_product_created_at_name
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'analysis_jobs'
  AND INDEX_NAME = 'idx_analysis_jobs_user_source_keyword_product_created_at';

SELECT COUNT(*) INTO @has_idx_user_source_keyword_product_created_at_equivalent
FROM (
  SELECT INDEX_NAME
  FROM INFORMATION_SCHEMA.STATISTICS
  WHERE TABLE_SCHEMA = @target_db
    AND TABLE_NAME = 'analysis_jobs'
  GROUP BY INDEX_NAME
  HAVING GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX SEPARATOR ',') = 'user_id,source,search_keyword,product_id,created_at'
) AS t;

SET @sql_add_idx_user_source_keyword_product_created_at = IF(
  @has_analysis_jobs_table = 0,
  'SELECT ''skip add idx_analysis_jobs_user_source_keyword_product_created_at (analysis_jobs missing)''',
  IF(
    @has_idx_user_source_keyword_product_created_at_name > 0 OR @has_idx_user_source_keyword_product_created_at_equivalent > 0,
    'SELECT ''idx_analysis_jobs_user_source_keyword_product_created_at already exists or equivalent exists''',
    'ALTER TABLE analysis_jobs ADD INDEX idx_analysis_jobs_user_source_keyword_product_created_at (user_id, source, search_keyword, product_id, created_at)'
  )
);
PREPARE stmt_add_idx_user_source_keyword_product_created_at FROM @sql_add_idx_user_source_keyword_product_created_at;
EXECUTE stmt_add_idx_user_source_keyword_product_created_at;
DEALLOCATE PREPARE stmt_add_idx_user_source_keyword_product_created_at;
