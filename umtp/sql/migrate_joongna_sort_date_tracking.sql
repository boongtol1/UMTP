USE UMTP_RB;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_seen_table
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_seen_products';

SELECT COUNT(*) INTO @has_last_sort_date
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_seen_products'
  AND COLUMN_NAME = 'last_sort_date';
SET @sql_last_sort_date = IF(
  @has_seen_table = 0,
  'SELECT "joongna_seen_products table missing"',
  IF(
    @has_last_sort_date = 0,
    'ALTER TABLE joongna_seen_products ADD COLUMN last_sort_date DATETIME NULL AFTER last_refresh_key',
    'SELECT "last_sort_date already exists"'
  )
);
PREPARE stmt_last_sort_date FROM @sql_last_sort_date;
EXECUTE stmt_last_sort_date;
DEALLOCATE PREPARE stmt_last_sort_date;

SELECT COUNT(*) INTO @has_previous_sort_date
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_seen_products'
  AND COLUMN_NAME = 'previous_sort_date';
SET @sql_previous_sort_date = IF(
  @has_seen_table = 0,
  'SELECT "joongna_seen_products table missing"',
  IF(
    @has_previous_sort_date = 0,
    'ALTER TABLE joongna_seen_products ADD COLUMN previous_sort_date DATETIME NULL AFTER last_sort_date',
    'SELECT "previous_sort_date already exists"'
  )
);
PREPARE stmt_previous_sort_date FROM @sql_previous_sort_date;
EXECUTE stmt_previous_sort_date;
DEALLOCATE PREPARE stmt_previous_sort_date;

SELECT COUNT(*) INTO @has_sort_date_changed_count
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_seen_products'
  AND COLUMN_NAME = 'sort_date_changed_count';
SET @sql_sort_date_changed_count = IF(
  @has_seen_table = 0,
  'SELECT "joongna_seen_products table missing"',
  IF(
    @has_sort_date_changed_count = 0,
    'ALTER TABLE joongna_seen_products ADD COLUMN sort_date_changed_count INT NOT NULL DEFAULT 0 AFTER previous_sort_date',
    'SELECT "sort_date_changed_count already exists"'
  )
);
PREPARE stmt_sort_date_changed_count FROM @sql_sort_date_changed_count;
EXECUTE stmt_sort_date_changed_count;
DEALLOCATE PREPARE stmt_sort_date_changed_count;

SELECT COUNT(*) INTO @has_last_sort_date_changed_at
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'joongna_seen_products'
  AND COLUMN_NAME = 'last_sort_date_changed_at';
SET @sql_last_sort_date_changed_at = IF(
  @has_seen_table = 0,
  'SELECT "joongna_seen_products table missing"',
  IF(
    @has_last_sort_date_changed_at = 0,
    'ALTER TABLE joongna_seen_products ADD COLUMN last_sort_date_changed_at TIMESTAMP NULL AFTER sort_date_changed_count',
    'SELECT "last_sort_date_changed_at already exists"'
  )
);
PREPARE stmt_last_sort_date_changed_at FROM @sql_last_sort_date_changed_at;
EXECUTE stmt_last_sort_date_changed_at;
DEALLOCATE PREPARE stmt_last_sort_date_changed_at;

SET @sql_backfill_last_sort_date = IF(
  @has_seen_table = 0,
  'SELECT "joongna_seen_products table missing"',
  'UPDATE joongna_seen_products
   SET last_sort_date = COALESCE(
     last_sort_date,
     STR_TO_DATE(REPLACE(SUBSTRING_INDEX(sort_date, ''+'', 1), ''T'', '' ''), ''%Y-%m-%d %H:%i:%s'')
   )
   WHERE last_sort_date IS NULL
     AND sort_date IS NOT NULL
     AND LENGTH(TRIM(sort_date)) > 0'
);
PREPARE stmt_backfill_last_sort_date FROM @sql_backfill_last_sort_date;
EXECUTE stmt_backfill_last_sort_date;
DEALLOCATE PREPARE stmt_backfill_last_sort_date;
