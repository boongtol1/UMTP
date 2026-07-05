USE UMTP_RB;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_search_results_body_text
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'search_results'
  AND COLUMN_NAME = 'body_text';

SET @sql_search_results_body_text = IF(
  @has_search_results_body_text = 0,
  'ALTER TABLE search_results ADD COLUMN body_text TEXT NULL AFTER url',
  'SELECT "search_results.body_text exists"'
);

PREPARE stmt_search_results_body_text FROM @sql_search_results_body_text;
EXECUTE stmt_search_results_body_text;
DEALLOCATE PREPARE stmt_search_results_body_text;
