USE UMTP_RB;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_analysis_job_id
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'listing_analysis_results'
  AND COLUMN_NAME = 'analysis_job_id';
SET @sql_analysis_job_id = IF(
  @has_analysis_job_id = 0,
  'ALTER TABLE listing_analysis_results ADD COLUMN analysis_job_id BIGINT UNSIGNED NULL AFTER id',
  'SELECT "analysis_job_id exists"'
);
PREPARE stmt_analysis_job_id FROM @sql_analysis_job_id;
EXECUTE stmt_analysis_job_id;
DEALLOCATE PREPARE stmt_analysis_job_id;

SELECT COUNT(*) INTO @has_watch_rule_id
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'listing_analysis_results'
  AND COLUMN_NAME = 'watch_rule_id';
SET @sql_watch_rule_id = IF(
  @has_watch_rule_id = 0,
  'ALTER TABLE listing_analysis_results ADD COLUMN watch_rule_id BIGINT UNSIGNED NULL AFTER analysis_job_id',
  'SELECT "watch_rule_id exists"'
);
PREPARE stmt_watch_rule_id FROM @sql_watch_rule_id;
EXECUTE stmt_watch_rule_id;
DEALLOCATE PREPARE stmt_watch_rule_id;

SELECT COUNT(*) INTO @has_trigger_reason
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'listing_analysis_results'
  AND COLUMN_NAME = 'trigger_reason';
SET @sql_trigger_reason = IF(
  @has_trigger_reason = 0,
  'ALTER TABLE listing_analysis_results ADD COLUMN trigger_reason VARCHAR(100) NULL AFTER watch_rule_id',
  'SELECT "trigger_reason exists"'
);
PREPARE stmt_trigger_reason FROM @sql_trigger_reason;
EXECUTE stmt_trigger_reason;
DEALLOCATE PREPARE stmt_trigger_reason;

SELECT COUNT(*) INTO @has_search_keyword
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'listing_analysis_results'
  AND COLUMN_NAME = 'search_keyword';
SET @sql_search_keyword = IF(
  @has_search_keyword = 0,
  'ALTER TABLE listing_analysis_results ADD COLUMN search_keyword VARCHAR(255) NULL AFTER trigger_reason',
  'SELECT "search_keyword exists"'
);
PREPARE stmt_search_keyword FROM @sql_search_keyword;
EXECUTE stmt_search_keyword;
DEALLOCATE PREPARE stmt_search_keyword;

SELECT COUNT(*) INTO @has_matched_watch_rule
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'listing_analysis_results'
  AND COLUMN_NAME = 'matched_watch_rule';
SET @sql_matched_watch_rule = IF(
  @has_matched_watch_rule = 0,
  'ALTER TABLE listing_analysis_results ADD COLUMN matched_watch_rule BOOLEAN NULL AFTER search_keyword',
  'SELECT "matched_watch_rule exists"'
);
PREPARE stmt_matched_watch_rule FROM @sql_matched_watch_rule;
EXECUTE stmt_matched_watch_rule;
DEALLOCATE PREPARE stmt_matched_watch_rule;

SELECT COUNT(*) INTO @has_alert_created
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'listing_analysis_results'
  AND COLUMN_NAME = 'alert_created';
SET @sql_alert_created = IF(
  @has_alert_created = 0,
  'ALTER TABLE listing_analysis_results ADD COLUMN alert_created BOOLEAN NOT NULL DEFAULT FALSE AFTER matched_watch_rule',
  'SELECT "alert_created exists"'
);
PREPARE stmt_alert_created FROM @sql_alert_created;
EXECUTE stmt_alert_created;
DEALLOCATE PREPARE stmt_alert_created;
