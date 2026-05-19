USE UMTP_RB;

SET @schema_name = DATABASE();

SET @has_user_fair_prices_table = (
  SELECT COUNT(*)
  FROM information_schema.tables
  WHERE table_schema = @schema_name
    AND table_name = 'user_fair_prices'
);

SET @has_user_fair_prices_priority = (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @schema_name
    AND table_name = 'user_fair_prices'
    AND column_name = 'priority'
);

SET @sql_user_fair_prices_priority = IF(
  @has_user_fair_prices_table = 0,
  'SELECT ''skip user_fair_prices.priority (table not found)''',
  IF(
    @has_user_fair_prices_priority > 0,
    'SELECT ''user_fair_prices.priority already exists''',
    'ALTER TABLE user_fair_prices ADD COLUMN priority VARCHAR(20) NOT NULL DEFAULT ''NORMAL'' AFTER poll_interval_seconds'
  )
);

PREPARE stmt_user_fair_prices_priority FROM @sql_user_fair_prices_priority;
EXECUTE stmt_user_fair_prices_priority;
DEALLOCATE PREPARE stmt_user_fair_prices_priority;

SET @sql_user_fair_prices_priority_backfill = IF(
  @has_user_fair_prices_table = 0,
  'SELECT ''skip user_fair_prices priority backfill (table not found)''',
  'UPDATE user_fair_prices
   SET priority = CASE
     WHEN UPPER(TRIM(priority)) = ''FAST'' THEN ''FAST''
     WHEN UPPER(TRIM(priority)) = ''LOW'' THEN ''LOW''
     ELSE ''NORMAL''
   END'
);

PREPARE stmt_user_fair_prices_priority_backfill FROM @sql_user_fair_prices_priority_backfill;
EXECUTE stmt_user_fair_prices_priority_backfill;
DEALLOCATE PREPARE stmt_user_fair_prices_priority_backfill;

SET @has_user_watch_rules_table = (
  SELECT COUNT(*)
  FROM information_schema.tables
  WHERE table_schema = @schema_name
    AND table_name = 'user_watch_rules'
);

SET @has_user_watch_rules_priority = (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @schema_name
    AND table_name = 'user_watch_rules'
    AND column_name = 'priority'
);

SET @sql_user_watch_rules_priority = IF(
  @has_user_watch_rules_table = 0,
  'SELECT ''skip user_watch_rules.priority (table not found)''',
  IF(
    @has_user_watch_rules_priority > 0,
    'SELECT ''user_watch_rules.priority already exists''',
    'ALTER TABLE user_watch_rules ADD COLUMN priority VARCHAR(20) NOT NULL DEFAULT ''NORMAL'' AFTER poll_interval_seconds'
  )
);

PREPARE stmt_user_watch_rules_priority FROM @sql_user_watch_rules_priority;
EXECUTE stmt_user_watch_rules_priority;
DEALLOCATE PREPARE stmt_user_watch_rules_priority;

SET @sql_user_watch_rules_priority_backfill = IF(
  @has_user_watch_rules_table = 0,
  'SELECT ''skip user_watch_rules priority backfill (table not found)''',
  'UPDATE user_watch_rules
   SET priority = CASE
     WHEN UPPER(TRIM(priority)) = ''FAST'' THEN ''FAST''
     WHEN UPPER(TRIM(priority)) = ''LOW'' THEN ''LOW''
     ELSE ''NORMAL''
   END'
);

PREPARE stmt_user_watch_rules_priority_backfill FROM @sql_user_watch_rules_priority_backfill;
EXECUTE stmt_user_watch_rules_priority_backfill;
DEALLOCATE PREPARE stmt_user_watch_rules_priority_backfill;
