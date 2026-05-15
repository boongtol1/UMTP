USE UMTP_RB;

SET @schema_name = DATABASE();

-- -----------------------------------------------------------------------------
-- UMTP Identity Migration
-- analysis identity: user_id + product_id
-- alert identity:    user_id + product_id
-- watch_rule_id 컬럼은 drop하지 않고 deprecated 상태로 유지합니다.
-- -----------------------------------------------------------------------------

-- [1] 기존 중복 정리 (최신 id 유지)
-- 주의: user_id/product_id가 NULL 또는 공백인 레코드는 제외합니다.
DELETE aj_old
FROM analysis_jobs aj_old
JOIN analysis_jobs aj_new
  ON aj_old.user_id = aj_new.user_id
 AND aj_old.product_id = aj_new.product_id
 AND aj_old.id < aj_new.id
WHERE aj_old.user_id IS NOT NULL
  AND TRIM(aj_old.user_id) <> ''
  AND aj_old.product_id IS NOT NULL
  AND TRIM(aj_old.product_id) <> '';

DELETE ae_old
FROM alert_events ae_old
JOIN alert_events ae_new
  ON ae_old.user_id = ae_new.user_id
 AND ae_old.product_id = ae_new.product_id
 AND ae_old.id < ae_new.id
WHERE ae_old.user_id IS NOT NULL
  AND TRIM(ae_old.user_id) <> ''
  AND ae_old.product_id IS NOT NULL
  AND TRIM(ae_old.product_id) <> '';

-- [2] analysis_jobs unique(user_id, product_id)
SELECT COUNT(*) INTO @has_uq_analysis_user_product
FROM (
  SELECT index_name
  FROM information_schema.statistics
  WHERE table_schema = @schema_name
    AND table_name = 'analysis_jobs'
    AND non_unique = 0
  GROUP BY index_name
  HAVING COUNT(*) = 2
     AND SUM(column_name = 'user_id') = 1
     AND SUM(column_name = 'product_id') = 1
) AS uq;

SET @sql_add_uq_analysis_user_product = IF(
  @has_uq_analysis_user_product > 0,
  'SELECT ''analysis_jobs unique(user_id, product_id) already exists''',
  'ALTER TABLE analysis_jobs ADD UNIQUE KEY uq_analysis_jobs_user_product (user_id, product_id)'
);
PREPARE stmt_add_uq_analysis_user_product FROM @sql_add_uq_analysis_user_product;
EXECUTE stmt_add_uq_analysis_user_product;
DEALLOCATE PREPARE stmt_add_uq_analysis_user_product;

-- [3] alert_events unique(user_id, product_id)
SELECT COUNT(*) INTO @has_uq_alert_user_product
FROM (
  SELECT index_name
  FROM information_schema.statistics
  WHERE table_schema = @schema_name
    AND table_name = 'alert_events'
    AND non_unique = 0
  GROUP BY index_name
  HAVING COUNT(*) = 2
     AND SUM(column_name = 'user_id') = 1
     AND SUM(column_name = 'product_id') = 1
) AS uq;

SET @sql_add_uq_alert_user_product = IF(
  @has_uq_alert_user_product > 0,
  'SELECT ''alert_events unique(user_id, product_id) already exists''',
  'ALTER TABLE alert_events ADD UNIQUE KEY uq_alert_events_user_product (user_id, product_id)'
);
PREPARE stmt_add_uq_alert_user_product FROM @sql_add_uq_alert_user_product;
EXECUTE stmt_add_uq_alert_user_product;
DEALLOCATE PREPARE stmt_add_uq_alert_user_product;

-- [4] Deprecated note (DDL 변경 없음)
SELECT 'watch_rule_id columns are kept as deprecated metadata (no DROP applied)' AS deprecation_note;
