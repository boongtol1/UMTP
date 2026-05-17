USE UMTP_RB;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_alert_events_table
FROM information_schema.tables
WHERE table_schema = @target_db
  AND table_name = 'alert_events';

SELECT COUNT(*) INTO @has_alert_events_body_text
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'alert_events'
  AND column_name = 'body_text';
SET @sql_alert_events_body_text = IF(
  @has_alert_events_table = 0,
  'SELECT ''skip alert_events.body_text''',
  IF(
    @has_alert_events_body_text = 0,
    'ALTER TABLE alert_events ADD COLUMN body_text TEXT NULL AFTER body_excerpt',
    'SELECT ''alert_events.body_text exists'''
  )
);
PREPARE stmt_alert_events_body_text FROM @sql_alert_events_body_text;
EXECUTE stmt_alert_events_body_text;
DEALLOCATE PREPARE stmt_alert_events_body_text;

SELECT COUNT(*) INTO @has_listing_results_table
FROM information_schema.tables
WHERE table_schema = @target_db
  AND table_name = 'listing_analysis_results';

SELECT COUNT(*) INTO @has_listing_results_body_text
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'listing_analysis_results'
  AND column_name = 'body_text';
SET @sql_listing_results_body_text = IF(
  @has_listing_results_table = 0,
  'SELECT ''skip listing_analysis_results.body_text''',
  IF(
    @has_listing_results_body_text = 0,
    'ALTER TABLE listing_analysis_results ADD COLUMN body_text TEXT NULL AFTER title',
    'SELECT ''listing_analysis_results.body_text exists'''
  )
);
PREPARE stmt_listing_results_body_text FROM @sql_listing_results_body_text;
EXECUTE stmt_listing_results_body_text;
DEALLOCATE PREPARE stmt_listing_results_body_text;

SELECT COUNT(*) INTO @has_url_logs_table
FROM information_schema.tables
WHERE table_schema = @target_db
  AND table_name = 'url_analysis_logs';

SELECT COUNT(*) INTO @has_url_logs_body_text
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'url_analysis_logs'
  AND column_name = 'body_text';
SET @sql_url_logs_body_text = IF(
  @has_url_logs_table = 0,
  'SELECT ''skip url_analysis_logs.body_text''',
  IF(
    @has_url_logs_body_text = 0,
    'ALTER TABLE url_analysis_logs ADD COLUMN body_text TEXT NULL AFTER title',
    'SELECT ''url_analysis_logs.body_text exists'''
  )
);
PREPARE stmt_url_logs_body_text FROM @sql_url_logs_body_text;
EXECUTE stmt_url_logs_body_text;
DEALLOCATE PREPARE stmt_url_logs_body_text;
