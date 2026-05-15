USE UMTP_RB;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_analysis_jobs_watch_rule_id
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'analysis_jobs'
  AND COLUMN_NAME = 'watch_rule_id';
SET @sql_drop_analysis_jobs_watch_rule_id = IF(
  @has_analysis_jobs_watch_rule_id = 0,
  'SELECT "analysis_jobs.watch_rule_id already dropped"',
  'ALTER TABLE analysis_jobs DROP COLUMN watch_rule_id'
);
PREPARE stmt_drop_analysis_jobs_watch_rule_id FROM @sql_drop_analysis_jobs_watch_rule_id;
EXECUTE stmt_drop_analysis_jobs_watch_rule_id;
DEALLOCATE PREPARE stmt_drop_analysis_jobs_watch_rule_id;

SELECT COUNT(*) INTO @has_alert_events_watch_rule_id
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'alert_events'
  AND COLUMN_NAME = 'watch_rule_id';
SET @sql_drop_alert_events_watch_rule_id = IF(
  @has_alert_events_watch_rule_id = 0,
  'SELECT "alert_events.watch_rule_id already dropped"',
  'ALTER TABLE alert_events DROP COLUMN watch_rule_id'
);
PREPARE stmt_drop_alert_events_watch_rule_id FROM @sql_drop_alert_events_watch_rule_id;
EXECUTE stmt_drop_alert_events_watch_rule_id;
DEALLOCATE PREPARE stmt_drop_alert_events_watch_rule_id;

SELECT COUNT(*) INTO @has_lar_watch_rule_id
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'listing_analysis_results'
  AND COLUMN_NAME = 'watch_rule_id';
SET @sql_drop_lar_watch_rule_id = IF(
  @has_lar_watch_rule_id = 0,
  'SELECT "listing_analysis_results.watch_rule_id already dropped"',
  'ALTER TABLE listing_analysis_results DROP COLUMN watch_rule_id'
);
PREPARE stmt_drop_lar_watch_rule_id FROM @sql_drop_lar_watch_rule_id;
EXECUTE stmt_drop_lar_watch_rule_id;
DEALLOCATE PREPARE stmt_drop_lar_watch_rule_id;

SELECT COUNT(*) INTO @has_lar_matched_watch_rule
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'listing_analysis_results'
  AND COLUMN_NAME = 'matched_watch_rule';
SET @sql_drop_lar_matched_watch_rule = IF(
  @has_lar_matched_watch_rule = 0,
  'SELECT "listing_analysis_results.matched_watch_rule already dropped"',
  'ALTER TABLE listing_analysis_results DROP COLUMN matched_watch_rule'
);
PREPARE stmt_drop_lar_matched_watch_rule FROM @sql_drop_lar_matched_watch_rule;
EXECUTE stmt_drop_lar_matched_watch_rule;
DEALLOCATE PREPARE stmt_drop_lar_matched_watch_rule;
