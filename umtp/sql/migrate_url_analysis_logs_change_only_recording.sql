USE UMTP_RB;

SET @target_db = DATABASE();

SELECT COUNT(*) INTO @has_url_analysis_logs
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs';

SELECT COUNT(*) INTO @has_content_signature
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'content_signature';
SET @sql_add_content_signature = IF(
  @has_url_analysis_logs = 0,
  'SELECT ''skip url_analysis_logs.content_signature (table missing)''',
  IF(
    @has_content_signature = 0,
    'ALTER TABLE url_analysis_logs ADD COLUMN content_signature VARCHAR(64) NOT NULL DEFAULT '''' AFTER reason',
    'SELECT ''url_analysis_logs.content_signature exists'''
  )
);
PREPARE stmt_add_content_signature FROM @sql_add_content_signature;
EXECUTE stmt_add_content_signature;
DEALLOCATE PREPARE stmt_add_content_signature;

SELECT COUNT(*) INTO @has_body_text
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'body_text';
SELECT COUNT(*) INTO @has_confidence_score
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'confidence_score';
SELECT COUNT(*) INTO @has_screen_inch_defaulted
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'screen_inch_defaulted';
SELECT COUNT(*) INTO @has_unit_valid
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'unit_valid';
SELECT COUNT(*) INTO @has_unit_validation_reason
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'unit_validation_reason';
SELECT COUNT(*) INTO @has_risk_detected
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'risk_detected';
SELECT COUNT(*) INTO @has_risk_level
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'risk_level';
SELECT COUNT(*) INTO @has_risk_score
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'risk_score';
SELECT COUNT(*) INTO @has_risk_keywords
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'risk_keywords';
SELECT COUNT(*) INTO @has_risk_categories
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'risk_categories';
SELECT COUNT(*) INTO @has_is_exchange_post
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'is_exchange_post';
SELECT COUNT(*) INTO @has_exchange_strength
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'exchange_strength';
SELECT COUNT(*) INTO @has_exchange_keywords
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'exchange_keywords';
SELECT COUNT(*) INTO @has_trade_type
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND COLUMN_NAME = 'trade_type';

SET @sig_expr = CONCAT(
  "SHA2(CONCAT_WS('|',",
  "IFNULL(user_id,''),",
  "IFNULL(url,''),",
  "IFNULL(source,''),",
  "IFNULL(title,''),",
  IF(@has_body_text > 0, "IFNULL(body_text,''),", "'',"),
  "IFNULL(CAST(listing_price_krw AS CHAR),''),",
  "IFNULL(product_type,''),",
  "IFNULL(chip,''),",
  "IFNULL(CAST(screen_inch AS CHAR),''),",
  "IFNULL(CAST(ram_gb AS CHAR),''),",
  "IFNULL(CAST(ssd_gb AS CHAR),''),",
  "IFNULL(CAST(fair_price_krw AS CHAR),''),",
  "IFNULL(CAST(diff_ratio AS CHAR),''),",
  "IFNULL(CAST(is_alert_target AS CHAR),''),",
  "IFNULL(status,''),",
  "IFNULL(reason,''),",
  IF(@has_confidence_score > 0, "IFNULL(CAST(confidence_score AS CHAR),''),", "'',"),
  IF(@has_screen_inch_defaulted > 0, "IFNULL(CAST(screen_inch_defaulted AS CHAR),''),", "'',"),
  IF(@has_unit_valid > 0, "IFNULL(CAST(unit_valid AS CHAR),''),", "'',"),
  IF(@has_unit_validation_reason > 0, "IFNULL(unit_validation_reason,''),", "'',"),
  IF(@has_risk_detected > 0, "IFNULL(CAST(risk_detected AS CHAR),''),", "'',"),
  IF(@has_risk_level > 0, "IFNULL(risk_level,''),", "'',"),
  IF(@has_risk_score > 0, "IFNULL(CAST(risk_score AS CHAR),''),", "'',"),
  IF(@has_risk_keywords > 0, "IFNULL(SHA2(IFNULL(risk_keywords,''), 256),''),", "'',"),
  IF(@has_risk_categories > 0, "IFNULL(SHA2(IFNULL(risk_categories,''), 256),''),", "'',"),
  IF(@has_is_exchange_post > 0, "IFNULL(CAST(is_exchange_post AS CHAR),''),", "'',"),
  IF(@has_exchange_strength > 0, "IFNULL(exchange_strength,''),", "'',"),
  IF(@has_exchange_keywords > 0, "IFNULL(SHA2(IFNULL(exchange_keywords,''), 256),''),", "'',"),
  IF(@has_trade_type > 0, "IFNULL(trade_type,''),", "'',"),
  "''), 256)"
);

SET @sql_backfill_content_signature = IF(
  @has_url_analysis_logs = 0,
  'SELECT ''skip backfill url_analysis_logs.content_signature (table missing)''',
  CONCAT(
    'UPDATE url_analysis_logs SET content_signature = ',
    @sig_expr,
    " WHERE content_signature IS NULL OR LENGTH(TRIM(content_signature)) = 0"
  )
);
PREPARE stmt_backfill_content_signature FROM @sql_backfill_content_signature;
EXECUTE stmt_backfill_content_signature;
DEALLOCATE PREPARE stmt_backfill_content_signature;

DROP TEMPORARY TABLE IF EXISTS tmp_keep_url_log_ids;
CREATE TEMPORARY TABLE tmp_keep_url_log_ids (
  id BIGINT UNSIGNED NOT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB;

SET @sql_insert_keep_ids = IF(
  @has_url_analysis_logs = 0,
  'SELECT ''skip dedupe keep-id build (table missing)''',
  'INSERT INTO tmp_keep_url_log_ids (id)
   SELECT MAX(ual.id) AS keep_id
   FROM url_analysis_logs ual
   GROUP BY ual.user_id, ual.content_signature'
);
PREPARE stmt_insert_keep_ids FROM @sql_insert_keep_ids;
EXECUTE stmt_insert_keep_ids;
DEALLOCATE PREPARE stmt_insert_keep_ids;

SET @sql_delete_duplicate_rows = IF(
  @has_url_analysis_logs = 0,
  'SELECT ''skip dedupe delete (table missing)''',
  'DELETE ual
   FROM url_analysis_logs ual
   LEFT JOIN tmp_keep_url_log_ids keep_ids
     ON keep_ids.id = ual.id
   WHERE keep_ids.id IS NULL'
);
PREPARE stmt_delete_duplicate_rows FROM @sql_delete_duplicate_rows;
EXECUTE stmt_delete_duplicate_rows;
DEALLOCATE PREPARE stmt_delete_duplicate_rows;

SET @deleted_duplicate_url_analysis_logs = IF(@has_url_analysis_logs = 0, 0, ROW_COUNT());
SELECT @deleted_duplicate_url_analysis_logs AS deleted_duplicate_url_analysis_logs;

SELECT COUNT(*) INTO @has_uq_user_signature
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND INDEX_NAME = 'uq_url_analysis_logs_user_signature';

SELECT GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX SEPARATOR ',')
INTO @uq_user_signature_columns
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND INDEX_NAME = 'uq_url_analysis_logs_user_signature';

SET @sql_drop_uq_user_signature_mismatch = IF(
  @has_url_analysis_logs = 0,
  'SELECT ''skip drop uq_url_analysis_logs_user_signature mismatch (table missing)''',
  IF(
    @has_uq_user_signature > 0
    AND IFNULL(@uq_user_signature_columns, '') <> 'user_id,content_signature',
    'ALTER TABLE url_analysis_logs DROP INDEX uq_url_analysis_logs_user_signature',
    'SELECT ''uq_url_analysis_logs_user_signature definition ok'''
  )
);
PREPARE stmt_drop_uq_user_signature_mismatch FROM @sql_drop_uq_user_signature_mismatch;
EXECUTE stmt_drop_uq_user_signature_mismatch;
DEALLOCATE PREPARE stmt_drop_uq_user_signature_mismatch;

SELECT COUNT(*) INTO @has_uq_user_signature_after_drop
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = @target_db
  AND TABLE_NAME = 'url_analysis_logs'
  AND INDEX_NAME = 'uq_url_analysis_logs_user_signature';

SET @sql_add_uq_user_signature = IF(
  @has_url_analysis_logs = 0,
  'SELECT ''skip add uq_url_analysis_logs_user_signature (table missing)''',
  IF(
    @has_uq_user_signature_after_drop = 0,
    'ALTER TABLE url_analysis_logs ADD UNIQUE KEY uq_url_analysis_logs_user_signature (user_id, content_signature)',
    'SELECT ''uq_url_analysis_logs_user_signature exists'''
  )
);
PREPARE stmt_add_uq_user_signature FROM @sql_add_uq_user_signature;
EXECUTE stmt_add_uq_user_signature;
DEALLOCATE PREPARE stmt_add_uq_user_signature;

SET @sql_final_row_count = IF(
  @has_url_analysis_logs = 0,
  'SELECT ''url_analysis_logs'' AS table_name, 0 AS row_count',
  'SELECT ''url_analysis_logs'' AS table_name, COUNT(*) AS row_count FROM url_analysis_logs'
);
PREPARE stmt_final_row_count FROM @sql_final_row_count;
EXECUTE stmt_final_row_count;
DEALLOCATE PREPARE stmt_final_row_count;
