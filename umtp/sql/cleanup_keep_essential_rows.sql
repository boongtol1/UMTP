USE UMTP_RB;

SET @cleanup_started_at = NOW();
SET SQL_SAFE_UPDATES = 0;

-- 정책:
-- - alert_events / alert_read_archive_events: 전량 보존 (삭제 없음)
-- - search_queries: 전량 보존 (삭제 없음)
-- - search_results: (search_query_id, product_id) 최신 1행만 유지
-- - url_analysis_logs: 완전 동일(content_signature 동일)한 행만 중복 제거
-- - joongna_seen_products: 활성 키워드와 일치하는 행만 유지

-- 1) 활성 키워드(현재 enabled watch rule) 집합
CREATE TEMPORARY TABLE tmp_enabled_keywords (
  keyword VARCHAR(255) COLLATE utf8mb4_0900_ai_ci NOT NULL,
  PRIMARY KEY (keyword)
) ENGINE=MEMORY;

INSERT INTO tmp_enabled_keywords (keyword)
SELECT DISTINCT (LOWER(TRIM(search_keyword)) COLLATE utf8mb4_0900_ai_ci)
FROM user_fair_prices
WHERE enabled = 1
  AND search_keyword IS NOT NULL
  AND TRIM(search_keyword) <> '';

-- 2) 유지할 search_results: 전체 범위에서 (query_id, product_id) 최신 1행
CREATE TEMPORARY TABLE tmp_keep_search_result_ids (
  id BIGINT UNSIGNED NOT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB;

INSERT INTO tmp_keep_search_result_ids (id)
SELECT MAX(sr.id) AS keep_id
FROM search_results sr
GROUP BY sr.search_query_id, sr.product_id;

DELETE sr
FROM search_results sr
LEFT JOIN tmp_keep_search_result_ids k
  ON k.id = sr.id
WHERE k.id IS NULL;
SELECT ROW_COUNT() AS deleted_search_results;

SELECT 0 AS deleted_search_queries;

-- 3) 유지할 url_analysis_logs: (user_id, content_signature) 최신 1행
-- 참고: migrate_url_analysis_logs_change_only_recording.sql 실행 후 사용 권장
CREATE TEMPORARY TABLE tmp_keep_url_log_ids (
  id BIGINT UNSIGNED NOT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB;

INSERT INTO tmp_keep_url_log_ids (id)
SELECT MAX(ual.id) AS keep_id
FROM url_analysis_logs ual
GROUP BY
  ual.user_id,
  COALESCE(
    NULLIF(TRIM(ual.content_signature), ''),
    SHA2(
      CONCAT_WS(
        '|',
        IFNULL(ual.user_id, ''),
        IFNULL(ual.url, ''),
        IFNULL(ual.source, ''),
        IFNULL(ual.title, ''),
        IFNULL(CAST(ual.listing_price_krw AS CHAR), ''),
        IFNULL(ual.product_type, ''),
        IFNULL(ual.chip, ''),
        IFNULL(CAST(ual.screen_inch AS CHAR), ''),
        IFNULL(CAST(ual.ram_gb AS CHAR), ''),
        IFNULL(CAST(ual.ssd_gb AS CHAR), ''),
        IFNULL(CAST(ual.fair_price_krw AS CHAR), ''),
        IFNULL(CAST(ual.diff_ratio AS CHAR), ''),
        IFNULL(CAST(ual.is_alert_target AS CHAR), ''),
        IFNULL(ual.status, ''),
        IFNULL(ual.reason, '')
      ),
      256
    )
  );

DELETE ual
FROM url_analysis_logs ual
LEFT JOIN tmp_keep_url_log_ids k
  ON k.id = ual.id
WHERE k.id IS NULL;
SELECT ROW_COUNT() AS deleted_url_analysis_logs;

SELECT 0 AS deleted_alert_events;
SELECT 0 AS deleted_alert_read_archive_events;

-- 4) 유지할 joongna_seen_products: 활성 키워드와 일치하는 행
CREATE TEMPORARY TABLE tmp_keep_seen_seq (
  seq BIGINT UNSIGNED NOT NULL,
  PRIMARY KEY (seq)
) ENGINE=MEMORY;

INSERT INTO tmp_keep_seen_seq (seq)
SELECT jsp.seq
FROM joongna_seen_products jsp
JOIN tmp_enabled_keywords ek
  ON (LOWER(TRIM(jsp.search_word)) COLLATE utf8mb4_0900_ai_ci) = ek.keyword;

DELETE jsp
FROM joongna_seen_products jsp
LEFT JOIN tmp_keep_seen_seq ks
  ON ks.seq = jsp.seq
WHERE ks.seq IS NULL;
SELECT ROW_COUNT() AS deleted_joongna_seen_products;

-- 5) 결과 집계
SELECT
  @cleanup_started_at AS cleanup_started_at,
  NOW() AS cleanup_finished_at;

SELECT 'search_results' AS table_name, COUNT(*) AS row_count FROM search_results
UNION ALL
SELECT 'search_queries', COUNT(*) FROM search_queries
UNION ALL
SELECT 'url_analysis_logs', COUNT(*) FROM url_analysis_logs
UNION ALL
SELECT 'alert_events', COUNT(*) FROM alert_events
UNION ALL
SELECT 'alert_read_archive_events', COUNT(*) FROM alert_read_archive_events
UNION ALL
SELECT 'joongna_seen_products', COUNT(*) FROM joongna_seen_products
UNION ALL
SELECT 'analysis_jobs', COUNT(*) FROM analysis_jobs
UNION ALL
SELECT 'listing_analysis_results', COUNT(*) FROM listing_analysis_results;
