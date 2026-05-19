USE UMTP_RB;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_analysis_jobs_table
FROM information_schema.tables
WHERE table_schema = @target_db
  AND table_name = 'analysis_jobs';

SELECT COUNT(*) INTO @has_analysis_jobs_sort_date
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'analysis_jobs'
  AND column_name = 'sort_date';
SET @sql_analysis_jobs_sort_date = IF(
  @has_analysis_jobs_table = 0,
  'SELECT ''skip analysis_jobs.sort_date''',
  IF(
    @has_analysis_jobs_sort_date = 0,
    'ALTER TABLE analysis_jobs ADD COLUMN sort_date DATETIME NULL AFTER watch_rule_id',
    'SELECT ''analysis_jobs.sort_date exists'''
  )
);
PREPARE stmt_analysis_jobs_sort_date FROM @sql_analysis_jobs_sort_date;
EXECUTE stmt_analysis_jobs_sort_date;
DEALLOCATE PREPARE stmt_analysis_jobs_sort_date;

SELECT COUNT(*) INTO @has_uq_analysis_jobs_user_rule_product
FROM information_schema.statistics
WHERE table_schema = @target_db
  AND table_name = 'analysis_jobs'
  AND index_name = 'uq_analysis_jobs_user_rule_product';

SELECT GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')
INTO @uq_analysis_jobs_user_rule_product_cols
FROM information_schema.statistics
WHERE table_schema = @target_db
  AND table_name = 'analysis_jobs'
  AND index_name = 'uq_analysis_jobs_user_rule_product';

SET @sql_drop_uq_analysis_jobs_user_rule_product_mismatch = IF(
  @has_analysis_jobs_table = 0,
  'SELECT ''skip drop uq_analysis_jobs_user_rule_product mismatch''',
  IF(
    @has_uq_analysis_jobs_user_rule_product = 1
    AND IFNULL(@uq_analysis_jobs_user_rule_product_cols, '') <> 'user_id,watch_rule_id,product_id,sort_date',
    'ALTER TABLE analysis_jobs DROP INDEX uq_analysis_jobs_user_rule_product',
    'SELECT ''uq_analysis_jobs_user_rule_product definition ok'''
  )
);
PREPARE stmt_drop_uq_analysis_jobs_user_rule_product_mismatch FROM @sql_drop_uq_analysis_jobs_user_rule_product_mismatch;
EXECUTE stmt_drop_uq_analysis_jobs_user_rule_product_mismatch;
DEALLOCATE PREPARE stmt_drop_uq_analysis_jobs_user_rule_product_mismatch;

SELECT COUNT(*) INTO @has_uq_analysis_jobs_user_rule_product_after_drop
FROM information_schema.statistics
WHERE table_schema = @target_db
  AND table_name = 'analysis_jobs'
  AND index_name = 'uq_analysis_jobs_user_rule_product';
SET @sql_uq_analysis_jobs_user_rule_product = IF(
  @has_analysis_jobs_table = 0,
  'SELECT ''skip add uq_analysis_jobs_user_rule_product''',
  IF(
    @has_uq_analysis_jobs_user_rule_product_after_drop = 0,
    'ALTER TABLE analysis_jobs ADD UNIQUE KEY uq_analysis_jobs_user_rule_product (user_id, watch_rule_id, product_id, sort_date)',
    'SELECT ''uq_analysis_jobs_user_rule_product exists'''
  )
);
PREPARE stmt_uq_analysis_jobs_user_rule_product FROM @sql_uq_analysis_jobs_user_rule_product;
EXECUTE stmt_uq_analysis_jobs_user_rule_product;
DEALLOCATE PREPARE stmt_uq_analysis_jobs_user_rule_product;

SELECT COUNT(*) INTO @has_alert_events_table
FROM information_schema.tables
WHERE table_schema = @target_db
  AND table_name = 'alert_events';

SELECT COUNT(*) INTO @has_alert_events_sort_date
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'alert_events'
  AND column_name = 'sort_date';
SET @sql_alert_events_sort_date = IF(
  @has_alert_events_table = 0,
  'SELECT ''skip alert_events.sort_date''',
  IF(
    @has_alert_events_sort_date = 0,
    'ALTER TABLE alert_events ADD COLUMN sort_date DATETIME NULL AFTER product_id',
    'SELECT ''alert_events.sort_date exists'''
  )
);
PREPARE stmt_alert_events_sort_date FROM @sql_alert_events_sort_date;
EXECUTE stmt_alert_events_sort_date;
DEALLOCATE PREPARE stmt_alert_events_sort_date;

SELECT COUNT(*) INTO @has_uq_alert_events_user_rule_product
FROM information_schema.statistics
WHERE table_schema = @target_db
  AND table_name = 'alert_events'
  AND index_name = 'uq_alert_events_user_rule_product';

SELECT GROUP_CONCAT(column_name ORDER BY seq_in_index SEPARATOR ',')
INTO @uq_alert_events_user_rule_product_cols
FROM information_schema.statistics
WHERE table_schema = @target_db
  AND table_name = 'alert_events'
  AND index_name = 'uq_alert_events_user_rule_product';

SET @sql_drop_uq_alert_events_user_rule_product_mismatch = IF(
  @has_alert_events_table = 0,
  'SELECT ''skip drop uq_alert_events_user_rule_product mismatch''',
  IF(
    @has_uq_alert_events_user_rule_product = 1
    AND IFNULL(@uq_alert_events_user_rule_product_cols, '') <> 'user_id,watch_rule_id,product_id,sort_date',
    'ALTER TABLE alert_events DROP INDEX uq_alert_events_user_rule_product',
    'SELECT ''uq_alert_events_user_rule_product definition ok'''
  )
);
PREPARE stmt_drop_uq_alert_events_user_rule_product_mismatch FROM @sql_drop_uq_alert_events_user_rule_product_mismatch;
EXECUTE stmt_drop_uq_alert_events_user_rule_product_mismatch;
DEALLOCATE PREPARE stmt_drop_uq_alert_events_user_rule_product_mismatch;

SELECT COUNT(*) INTO @has_uq_alert_events_user_rule_product_after_drop
FROM information_schema.statistics
WHERE table_schema = @target_db
  AND table_name = 'alert_events'
  AND index_name = 'uq_alert_events_user_rule_product';
SET @sql_uq_alert_events_user_rule_product = IF(
  @has_alert_events_table = 0,
  'SELECT ''skip add uq_alert_events_user_rule_product''',
  IF(
    @has_uq_alert_events_user_rule_product_after_drop = 0,
    'ALTER TABLE alert_events ADD UNIQUE KEY uq_alert_events_user_rule_product (user_id, watch_rule_id, product_id, sort_date)',
    'SELECT ''uq_alert_events_user_rule_product exists'''
  )
);
PREPARE stmt_uq_alert_events_user_rule_product FROM @sql_uq_alert_events_user_rule_product;
EXECUTE stmt_uq_alert_events_user_rule_product;
DEALLOCATE PREPARE stmt_uq_alert_events_user_rule_product;
