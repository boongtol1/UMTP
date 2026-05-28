USE UMTP_RB;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_search_results
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'search_results';

SELECT COUNT(*) INTO @has_refresh_key
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'search_results'
  AND COLUMN_NAME = 'refresh_key';
SET @sql_add_refresh_key = IF(
  @has_search_results = 0,
  'SELECT ''skip search_results.refresh_key (table missing)''',
  IF(
    @has_refresh_key = 0,
    'ALTER TABLE search_results ADD COLUMN refresh_key VARCHAR(255) NULL AFTER url',
    'SELECT ''search_results.refresh_key exists'''
  )
);
PREPARE stmt_add_refresh_key FROM @sql_add_refresh_key;
EXECUTE stmt_add_refresh_key;
DEALLOCATE PREPARE stmt_add_refresh_key;

SELECT COUNT(*) INTO @has_content_signature
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'search_results'
  AND COLUMN_NAME = 'content_signature';
SET @sql_add_content_signature = IF(
  @has_search_results = 0,
  'SELECT ''skip search_results.content_signature (table missing)''',
  IF(
    @has_content_signature = 0,
    'ALTER TABLE search_results ADD COLUMN content_signature VARCHAR(64) NOT NULL DEFAULT '''' AFTER raw_json',
    'SELECT ''search_results.content_signature exists'''
  )
);
PREPARE stmt_add_content_signature FROM @sql_add_content_signature;
EXECUTE stmt_add_content_signature;
DEALLOCATE PREPARE stmt_add_content_signature;

SET @sql_backfill_content_signature = IF(
  @has_search_results = 0,
  'SELECT ''skip backfill search_results.content_signature (table missing)''',
  'UPDATE search_results
   SET content_signature = SHA2(
     CONCAT_WS(
       ''|'',
       IFNULL(title, ''''),
       IFNULL(CAST(price AS CHAR), ''''),
       IFNULL(DATE_FORMAT(sort_date, ''%Y-%m-%d %H:%i:%s''), ''''),
       IFNULL(url, ''''),
       IFNULL(refresh_key, ''''),
       IFNULL(SHA2(IFNULL(raw_json, ''''), 256), '''')
     ),
     256
   )
   WHERE content_signature IS NULL OR LENGTH(TRIM(content_signature)) = 0'
);
PREPARE stmt_backfill_content_signature FROM @sql_backfill_content_signature;
EXECUTE stmt_backfill_content_signature;
DEALLOCATE PREPARE stmt_backfill_content_signature;

DROP TEMPORARY TABLE IF EXISTS tmp_keep_search_result_ids;
CREATE TEMPORARY TABLE tmp_keep_search_result_ids (
  id BIGINT UNSIGNED NOT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB;

SET @sql_insert_keep_ids = IF(
  @has_search_results = 0,
  'SELECT ''skip dedupe keep-id build (table missing)''',
  'INSERT INTO tmp_keep_search_result_ids (id)
   SELECT MAX(sr.id) AS keep_id
   FROM search_results sr
   GROUP BY sr.search_query_id, sr.product_id, sr.content_signature'
);
PREPARE stmt_insert_keep_ids FROM @sql_insert_keep_ids;
EXECUTE stmt_insert_keep_ids;
DEALLOCATE PREPARE stmt_insert_keep_ids;

SET @sql_delete_duplicate_rows = IF(
  @has_search_results = 0,
  'SELECT ''skip dedupe delete (table missing)''',
  'DELETE sr
   FROM search_results sr
   LEFT JOIN tmp_keep_search_result_ids keep_ids
     ON keep_ids.id = sr.id
   WHERE keep_ids.id IS NULL'
);
PREPARE stmt_delete_duplicate_rows FROM @sql_delete_duplicate_rows;
EXECUTE stmt_delete_duplicate_rows;
DEALLOCATE PREPARE stmt_delete_duplicate_rows;

SET @deleted_duplicate_search_results = IF(@has_search_results = 0, 0, ROW_COUNT());
SELECT @deleted_duplicate_search_results AS deleted_duplicate_search_results;

SELECT COUNT(*) INTO @has_uq_signature
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'search_results'
  AND INDEX_NAME = 'uq_search_results_query_product_signature';

SELECT GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX SEPARATOR ',')
INTO @uq_signature_columns
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'search_results'
  AND INDEX_NAME = 'uq_search_results_query_product_signature';

SET @sql_drop_uq_signature_mismatch = IF(
  @has_search_results = 0,
  'SELECT ''skip drop uq_search_results_query_product_signature mismatch (table missing)''',
  IF(
    @has_uq_signature > 0
    AND IFNULL(@uq_signature_columns, '') <> 'search_query_id,product_id,content_signature',
    'ALTER TABLE search_results DROP INDEX uq_search_results_query_product_signature',
    'SELECT ''uq_search_results_query_product_signature definition ok'''
  )
);
PREPARE stmt_drop_uq_signature_mismatch FROM @sql_drop_uq_signature_mismatch;
EXECUTE stmt_drop_uq_signature_mismatch;
DEALLOCATE PREPARE stmt_drop_uq_signature_mismatch;

SELECT COUNT(*) INTO @has_uq_signature_after_drop
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'search_results'
  AND INDEX_NAME = 'uq_search_results_query_product_signature';

SET @sql_add_uq_signature = IF(
  @has_search_results = 0,
  'SELECT ''skip add uq_search_results_query_product_signature (table missing)''',
  IF(
    @has_uq_signature_after_drop = 0,
    'ALTER TABLE search_results ADD UNIQUE KEY uq_search_results_query_product_signature (search_query_id, product_id, content_signature)',
    'SELECT ''uq_search_results_query_product_signature exists'''
  )
);
PREPARE stmt_add_uq_signature FROM @sql_add_uq_signature;
EXECUTE stmt_add_uq_signature;
DEALLOCATE PREPARE stmt_add_uq_signature;

SET @sql_final_row_count = IF(
  @has_search_results = 0,
  'SELECT ''search_results'' AS table_name, 0 AS row_count',
  'SELECT ''search_results'' AS table_name, COUNT(*) AS row_count FROM search_results'
);
PREPARE stmt_final_row_count FROM @sql_final_row_count;
EXECUTE stmt_final_row_count;
DEALLOCATE PREPARE stmt_final_row_count;
