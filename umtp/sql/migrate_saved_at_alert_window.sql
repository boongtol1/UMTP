USE UMTP_RB;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_user_fair_prices_table
FROM information_schema.tables
WHERE table_schema = @target_db
  AND table_name = 'user_fair_prices';

SELECT COUNT(*) INTO @has_saved_at
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'user_fair_prices'
  AND column_name = 'saved_at';
SET @sql_saved_at = IF(
  @has_user_fair_prices_table = 0,
  'SELECT ''skip user_fair_prices.saved_at''',
  IF(
    @has_saved_at = 0,
    'ALTER TABLE user_fair_prices ADD COLUMN saved_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP AFTER last_polled_at',
    'SELECT ''user_fair_prices.saved_at exists'''
  )
);
PREPARE stmt_saved_at FROM @sql_saved_at;
EXECUTE stmt_saved_at;
DEALLOCATE PREPARE stmt_saved_at;

SET @sql_backfill_saved_at = IF(
  @has_user_fair_prices_table = 0,
  'SELECT ''skip saved_at backfill''',
  'UPDATE user_fair_prices
   SET saved_at = COALESCE(saved_at, last_poll_requested_at, updated_at, created_at, CURRENT_TIMESTAMP)
   WHERE saved_at IS NULL'
);
PREPARE stmt_backfill_saved_at FROM @sql_backfill_saved_at;
EXECUTE stmt_backfill_saved_at;
DEALLOCATE PREPARE stmt_backfill_saved_at;

SELECT COUNT(*) INTO @has_analysis_jobs_table
FROM information_schema.tables
WHERE table_schema = @target_db
  AND table_name = 'analysis_jobs';

SELECT COUNT(*) INTO @has_analysis_jobs_watch_rule_id
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'analysis_jobs'
  AND column_name = 'watch_rule_id';
SET @sql_analysis_jobs_watch_rule_id = IF(
  @has_analysis_jobs_table = 0,
  'SELECT ''skip analysis_jobs.watch_rule_id''',
  IF(
    @has_analysis_jobs_watch_rule_id = 0,
    'ALTER TABLE analysis_jobs ADD COLUMN watch_rule_id BIGINT UNSIGNED NULL AFTER user_id',
    'SELECT ''analysis_jobs.watch_rule_id exists'''
  )
);
PREPARE stmt_analysis_jobs_watch_rule_id FROM @sql_analysis_jobs_watch_rule_id;
EXECUTE stmt_analysis_jobs_watch_rule_id;
DEALLOCATE PREPARE stmt_analysis_jobs_watch_rule_id;

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

SELECT COUNT(*) INTO @has_analysis_jobs_change_fingerprint
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'analysis_jobs'
  AND column_name = 'change_fingerprint';
SET @sql_analysis_jobs_change_fingerprint = IF(
  @has_analysis_jobs_table = 0,
  'SELECT ''skip analysis_jobs.change_fingerprint''',
  IF(
    @has_analysis_jobs_change_fingerprint = 0,
    'ALTER TABLE analysis_jobs ADD COLUMN change_fingerprint VARCHAR(64) NOT NULL DEFAULT '''' AFTER sort_date',
    'SELECT ''analysis_jobs.change_fingerprint exists'''
  )
);
PREPARE stmt_analysis_jobs_change_fingerprint FROM @sql_analysis_jobs_change_fingerprint;
EXECUTE stmt_analysis_jobs_change_fingerprint;
DEALLOCATE PREPARE stmt_analysis_jobs_change_fingerprint;

SET @sql_backfill_analysis_jobs_change_fingerprint = IF(
  @has_analysis_jobs_table = 0,
  'SELECT ''skip analysis_jobs.change_fingerprint backfill''',
  'UPDATE analysis_jobs
   SET change_fingerprint = SHA2(
     CONCAT_WS(
       ''|'',
       IFNULL(user_id, ''''),
       IFNULL(CAST(watch_rule_id AS CHAR), ''''),
       IFNULL(product_id, ''''),
       IFNULL(trigger_reason, ''''),
       IFNULL(DATE_FORMAT(sort_date, ''%Y-%m-%d %H:%i:%s''), ''''),
       IFNULL(title, ''''),
       IFNULL(CAST(price_krw AS CHAR), ''''),
       IFNULL(url, ''''),
       IFNULL(CAST(id AS CHAR), '''')
     ),
     256
   )
   WHERE change_fingerprint IS NULL OR LENGTH(TRIM(change_fingerprint)) = 0'
);
PREPARE stmt_backfill_analysis_jobs_change_fingerprint FROM @sql_backfill_analysis_jobs_change_fingerprint;
EXECUTE stmt_backfill_analysis_jobs_change_fingerprint;
DEALLOCATE PREPARE stmt_backfill_analysis_jobs_change_fingerprint;

SELECT COUNT(*) INTO @has_analysis_jobs_idx_sort_date
FROM information_schema.statistics
WHERE table_schema = @target_db
  AND table_name = 'analysis_jobs'
  AND index_name = 'idx_analysis_jobs_sort_date';
SET @sql_analysis_jobs_idx_sort_date = IF(
  @has_analysis_jobs_table = 0,
  'SELECT ''skip analysis_jobs.idx_sort_date''',
  IF(
    @has_analysis_jobs_idx_sort_date = 0,
    'ALTER TABLE analysis_jobs ADD INDEX idx_analysis_jobs_sort_date (sort_date)',
    'SELECT ''analysis_jobs.idx_sort_date exists'''
  )
);
PREPARE stmt_analysis_jobs_idx_sort_date FROM @sql_analysis_jobs_idx_sort_date;
EXECUTE stmt_analysis_jobs_idx_sort_date;
DEALLOCATE PREPARE stmt_analysis_jobs_idx_sort_date;

SELECT COUNT(*) INTO @has_uq_analysis_jobs_user_product
FROM information_schema.statistics
WHERE table_schema = @target_db
  AND table_name = 'analysis_jobs'
  AND index_name = 'uq_analysis_jobs_user_product';
SET @sql_drop_uq_analysis_jobs_user_product = IF(
  @has_analysis_jobs_table = 0,
  'SELECT ''skip drop uq_analysis_jobs_user_product''',
  IF(
    @has_uq_analysis_jobs_user_product = 0,
    'SELECT ''uq_analysis_jobs_user_product already absent''',
    'ALTER TABLE analysis_jobs DROP INDEX uq_analysis_jobs_user_product'
  )
);
PREPARE stmt_drop_uq_analysis_jobs_user_product FROM @sql_drop_uq_analysis_jobs_user_product;
EXECUTE stmt_drop_uq_analysis_jobs_user_product;
DEALLOCATE PREPARE stmt_drop_uq_analysis_jobs_user_product;

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
    @has_uq_analysis_jobs_user_rule_product > 0
    AND IFNULL(@uq_analysis_jobs_user_rule_product_cols, '') <> 'user_id,watch_rule_id,product_id,change_fingerprint',
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
    'ALTER TABLE analysis_jobs ADD UNIQUE KEY uq_analysis_jobs_user_rule_product (user_id, watch_rule_id, product_id, change_fingerprint)',
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

SELECT COUNT(*) INTO @has_alert_events_watch_rule_id
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'alert_events'
  AND column_name = 'watch_rule_id';
SET @sql_alert_events_watch_rule_id = IF(
  @has_alert_events_table = 0,
  'SELECT ''skip alert_events.watch_rule_id''',
  IF(
    @has_alert_events_watch_rule_id = 0,
    'ALTER TABLE alert_events ADD COLUMN watch_rule_id BIGINT UNSIGNED NULL AFTER user_id',
    'SELECT ''alert_events.watch_rule_id exists'''
  )
);
PREPARE stmt_alert_events_watch_rule_id FROM @sql_alert_events_watch_rule_id;
EXECUTE stmt_alert_events_watch_rule_id;
DEALLOCATE PREPARE stmt_alert_events_watch_rule_id;

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

SELECT COUNT(*) INTO @has_alert_events_change_fingerprint
FROM information_schema.columns
WHERE table_schema = @target_db
  AND table_name = 'alert_events'
  AND column_name = 'change_fingerprint';
SET @sql_alert_events_change_fingerprint = IF(
  @has_alert_events_table = 0,
  'SELECT ''skip alert_events.change_fingerprint''',
  IF(
    @has_alert_events_change_fingerprint = 0,
    'ALTER TABLE alert_events ADD COLUMN change_fingerprint VARCHAR(64) NOT NULL DEFAULT '''' AFTER sort_date',
    'SELECT ''alert_events.change_fingerprint exists'''
  )
);
PREPARE stmt_alert_events_change_fingerprint FROM @sql_alert_events_change_fingerprint;
EXECUTE stmt_alert_events_change_fingerprint;
DEALLOCATE PREPARE stmt_alert_events_change_fingerprint;

SET @sql_backfill_alert_events_change_fingerprint = IF(
  @has_alert_events_table = 0,
  'SELECT ''skip alert_events.change_fingerprint backfill''',
  'UPDATE alert_events
   SET change_fingerprint = SHA2(
     CONCAT_WS(
       ''|'',
       IFNULL(user_id, ''''),
       IFNULL(CAST(watch_rule_id AS CHAR), ''''),
       IFNULL(product_id, ''''),
       IFNULL(trigger_reason, ''''),
       IFNULL(DATE_FORMAT(sort_date, ''%Y-%m-%d %H:%i:%s''), ''''),
       IFNULL(title, ''''),
       IFNULL(CAST(price_krw AS CHAR), ''''),
       IFNULL(CAST(id AS CHAR), '''')
     ),
     256
   )
   WHERE change_fingerprint IS NULL OR LENGTH(TRIM(change_fingerprint)) = 0'
);
PREPARE stmt_backfill_alert_events_change_fingerprint FROM @sql_backfill_alert_events_change_fingerprint;
EXECUTE stmt_backfill_alert_events_change_fingerprint;
DEALLOCATE PREPARE stmt_backfill_alert_events_change_fingerprint;

SELECT COUNT(*) INTO @has_alert_events_idx_sort_date
FROM information_schema.statistics
WHERE table_schema = @target_db
  AND table_name = 'alert_events'
  AND index_name = 'idx_alert_events_sort_date';
SET @sql_alert_events_idx_sort_date = IF(
  @has_alert_events_table = 0,
  'SELECT ''skip alert_events.idx_sort_date''',
  IF(
    @has_alert_events_idx_sort_date = 0,
    'ALTER TABLE alert_events ADD INDEX idx_alert_events_sort_date (sort_date)',
    'SELECT ''alert_events.idx_sort_date exists'''
  )
);
PREPARE stmt_alert_events_idx_sort_date FROM @sql_alert_events_idx_sort_date;
EXECUTE stmt_alert_events_idx_sort_date;
DEALLOCATE PREPARE stmt_alert_events_idx_sort_date;

SELECT COUNT(*) INTO @has_uq_alert_events_user_product
FROM information_schema.statistics
WHERE table_schema = @target_db
  AND table_name = 'alert_events'
  AND index_name = 'uq_alert_events_user_product';
SET @sql_drop_uq_alert_events_user_product = IF(
  @has_alert_events_table = 0,
  'SELECT ''skip drop uq_alert_events_user_product''',
  IF(
    @has_uq_alert_events_user_product = 0,
    'SELECT ''uq_alert_events_user_product already absent''',
    'ALTER TABLE alert_events DROP INDEX uq_alert_events_user_product'
  )
);
PREPARE stmt_drop_uq_alert_events_user_product FROM @sql_drop_uq_alert_events_user_product;
EXECUTE stmt_drop_uq_alert_events_user_product;
DEALLOCATE PREPARE stmt_drop_uq_alert_events_user_product;

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
    @has_uq_alert_events_user_rule_product > 0
    AND IFNULL(@uq_alert_events_user_rule_product_cols, '') <> 'user_id,watch_rule_id,product_id,change_fingerprint',
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
    'ALTER TABLE alert_events ADD UNIQUE KEY uq_alert_events_user_rule_product (user_id, watch_rule_id, product_id, change_fingerprint)',
    'SELECT ''uq_alert_events_user_rule_product exists'''
  )
);
PREPARE stmt_uq_alert_events_user_rule_product FROM @sql_uq_alert_events_user_rule_product;
EXECUTE stmt_uq_alert_events_user_rule_product;
DEALLOCATE PREPARE stmt_uq_alert_events_user_rule_product;
