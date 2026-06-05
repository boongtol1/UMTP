USE UMTP_RB;

SET @cleanup_started_at = NOW();
SET SQL_SAFE_UPDATES = 0;

-- Policy:
-- - fraud_training_label_candidates: keep all rows; UNIQUE(product_id) already prevents duplicates.
-- - fraud_product_snapshots: keep product state changes plus the latest row per product.
-- - fraud_store_status_snapshots: keep status changes plus the latest row per store.
-- - fraud_store_activity_snapshots: keep activity/profile metric changes plus the latest row per store.
-- - fraud_store_profile_field_snapshots: keep profile field changes plus the latest row per store.
--
-- The cleanup removes consecutive duplicate snapshots only. If a state changes A -> B -> A,
-- both A rows are preserved because the second A is a meaningful change event.
-- Run a DB backup before executing this script on production data.

SELECT COUNT(*) INTO @before_fraud_product_snapshots
FROM fraud_product_snapshots;
SELECT COUNT(*) INTO @before_fraud_store_status_snapshots
FROM fraud_store_status_snapshots;
SELECT COUNT(*) INTO @before_fraud_store_activity_snapshots
FROM fraud_store_activity_snapshots;
SELECT COUNT(*) INTO @before_fraud_store_profile_field_snapshots
FROM fraud_store_profile_field_snapshots;
SELECT COUNT(*) INTO @before_fraud_training_label_candidates
FROM fraud_training_label_candidates;

-- 1) Product snapshots: keep state changes and latest observation per product.
CREATE TEMPORARY TABLE tmp_keep_fraud_product_snapshot_ids (
  id BIGINT NOT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB;

INSERT IGNORE INTO tmp_keep_fraud_product_snapshot_ids (id)
SELECT id
FROM (
  SELECT
    id,
    state_fingerprint,
    LAG(state_fingerprint) OVER (
      PARTITION BY product_id
      ORDER BY observed_at, id
    ) AS previous_state_fingerprint
  FROM (
    SELECT
      id,
      product_id,
      observed_at,
      SHA2(
        CAST(
          JSON_OBJECT(
            'store_id', store_id,
            'sort_date', DATE_FORMAT(sort_date, '%Y-%m-%d %H:%i:%s'),
            'price_krw', price_krw,
            'title_hash', title_hash,
            'title_text_hash', SHA2(title, 256),
            'body_hash', body_hash,
            'content_hash', content_hash,
            'source', source,
            'url_hash', SHA2(url, 256),
            'snapshot_reason', snapshot_reason
          ) AS CHAR
        ),
        256
      ) AS state_fingerprint
    FROM fraud_product_snapshots
  ) product_states
) ranked
WHERE previous_state_fingerprint IS NULL
   OR state_fingerprint <> previous_state_fingerprint;

INSERT IGNORE INTO tmp_keep_fraud_product_snapshot_ids (id)
SELECT id
FROM (
  SELECT
    id,
    ROW_NUMBER() OVER (
      PARTITION BY product_id
      ORDER BY observed_at DESC, id DESC
    ) AS row_number_for_product
  FROM fraud_product_snapshots
) latest
WHERE row_number_for_product = 1;

DELETE fps
FROM fraud_product_snapshots fps
LEFT JOIN tmp_keep_fraud_product_snapshot_ids keep_ids
  ON keep_ids.id = fps.id
WHERE keep_ids.id IS NULL;
SELECT ROW_COUNT() AS deleted_fraud_product_snapshots;

-- 2) Store status snapshots: keep status changes and latest check per store.
CREATE TEMPORARY TABLE tmp_keep_fraud_store_status_snapshot_ids (
  id BIGINT NOT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB;

INSERT IGNORE INTO tmp_keep_fraud_store_status_snapshot_ids (id)
SELECT id
FROM (
  SELECT
    id,
    state_fingerprint,
    LAG(state_fingerprint) OVER (
      PARTITION BY store_id
      ORDER BY checked_at, id
    ) AS previous_state_fingerprint
  FROM (
    SELECT
      id,
      store_id,
      checked_at,
      SHA2(
        CAST(
          JSON_OBJECT(
            'store_seq', store_seq,
            'status', status,
            'status_reason', status_reason,
            'source', source,
            'is_active', is_active,
            'http_status', http_status,
            'meta_code', meta_code,
            'meta_message', meta_message,
            'raw_status_text_hash', SHA2(raw_status_text, 256),
            'raw_snippet_hash', SHA2(raw_snippet, 256),
            'first_seen_product_id', first_seen_product_id,
            'first_seen_sort_date', DATE_FORMAT(first_seen_sort_date, '%Y-%m-%d %H:%i:%s'),
            'error_message_hash', SHA2(error_message, 256)
          ) AS CHAR
        ),
        256
      ) AS state_fingerprint
    FROM fraud_store_status_snapshots
  ) status_states
) ranked
WHERE previous_state_fingerprint IS NULL
   OR state_fingerprint <> previous_state_fingerprint;

INSERT IGNORE INTO tmp_keep_fraud_store_status_snapshot_ids (id)
SELECT id
FROM (
  SELECT
    id,
    ROW_NUMBER() OVER (
      PARTITION BY store_id
      ORDER BY checked_at DESC, id DESC
    ) AS row_number_for_store
  FROM fraud_store_status_snapshots
) latest
WHERE row_number_for_store = 1;

DELETE fsss
FROM fraud_store_status_snapshots fsss
LEFT JOIN tmp_keep_fraud_store_status_snapshot_ids keep_ids
  ON keep_ids.id = fsss.id
WHERE keep_ids.id IS NULL;
SELECT ROW_COUNT() AS deleted_fraud_store_status_snapshots;

-- 3) Store activity snapshots: keep metric changes and latest check per store.
CREATE TEMPORARY TABLE tmp_keep_fraud_store_activity_snapshot_ids (
  id BIGINT NOT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB;

INSERT IGNORE INTO tmp_keep_fraud_store_activity_snapshot_ids (id)
SELECT id
FROM (
  SELECT
    id,
    state_fingerprint,
    LAG(state_fingerprint) OVER (
      PARTITION BY store_id
      ORDER BY checked_at, id
    ) AS previous_state_fingerprint
  FROM (
    SELECT
      id,
      store_id,
      checked_at,
      SHA2(
        CAST(
          JSON_OBJECT(
            'store_seq', store_seq,
            'posts_last_1h', posts_last_1h,
            'posts_last_6h', posts_last_6h,
            'posts_last_24h', posts_last_24h,
            'posts_last_7d', posts_last_7d,
            'visible_product_count', visible_product_count,
            'store_name_fingerprint', store_name_fingerprint,
            'profile_fingerprint', profile_fingerprint,
            'profile_image_url_hash', SHA2(profile_image_url, 256),
            'has_default_profile_image', has_default_profile_image,
            'store_level', store_level,
            'store_level_number', store_level_number,
            'review_count', review_count,
            'reliability_score', reliability_score,
            'activity_score', activity_score,
            'notified_score', notified_score,
            'safe_trade_count', safe_trade_count,
            'trust_score', trust_score,
            'chat_response_ratio', chat_response_ratio,
            'chat_response_time', chat_response_time,
            'chat_response_time_text', chat_response_time_text,
            'visit_today_count', visit_today_count,
            'visit_total_count', visit_total_count,
            'store_grade', store_grade,
            'user_type', user_type,
            'partner_center_seller_yn', partner_center_seller_yn,
            'is_official_account', is_official_account,
            'store_desc_hash', SHA2(store_desc, 256),
            'first_seen_product_id', first_seen_product_id,
            'first_seen_sort_date', DATE_FORMAT(first_seen_sort_date, '%Y-%m-%d %H:%i:%s')
          ) AS CHAR
        ),
        256
      ) AS state_fingerprint
    FROM fraud_store_activity_snapshots
  ) activity_states
) ranked
WHERE previous_state_fingerprint IS NULL
   OR state_fingerprint <> previous_state_fingerprint;

INSERT IGNORE INTO tmp_keep_fraud_store_activity_snapshot_ids (id)
SELECT id
FROM (
  SELECT
    id,
    ROW_NUMBER() OVER (
      PARTITION BY store_id
      ORDER BY checked_at DESC, id DESC
    ) AS row_number_for_store
  FROM fraud_store_activity_snapshots
) latest
WHERE row_number_for_store = 1;

DELETE fsas
FROM fraud_store_activity_snapshots fsas
LEFT JOIN tmp_keep_fraud_store_activity_snapshot_ids keep_ids
  ON keep_ids.id = fsas.id
WHERE keep_ids.id IS NULL;
SELECT ROW_COUNT() AS deleted_fraud_store_activity_snapshots;

-- 4) Store profile field snapshots: keep profile metric changes and latest check per store.
CREATE TEMPORARY TABLE tmp_keep_fraud_store_profile_field_snapshot_ids (
  id BIGINT NOT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB;

INSERT IGNORE INTO tmp_keep_fraud_store_profile_field_snapshot_ids (id)
SELECT id
FROM (
  SELECT
    id,
    state_fingerprint,
    LAG(state_fingerprint) OVER (
      PARTITION BY store_id
      ORDER BY checked_at, id
    ) AS previous_state_fingerprint
  FROM (
    SELECT
      id,
      store_id,
      checked_at,
      SHA2(
        CAST(
          JSON_OBJECT(
            'store_seq', store_seq,
            'status', status,
            'source', source,
            'trust_score', trust_score,
            'review_count', review_count,
            'store_level', store_level,
            'store_level_number', store_level_number,
            'safe_trade_count', safe_trade_count,
            'reliability_score', reliability_score,
            'activity_score', activity_score,
            'notified_score', notified_score,
            'visit_today_count', visit_today_count,
            'visit_total_count', visit_total_count,
            'is_official_account', is_official_account
          ) AS CHAR
        ),
        256
      ) AS state_fingerprint
    FROM fraud_store_profile_field_snapshots
  ) profile_field_states
) ranked
WHERE previous_state_fingerprint IS NULL
   OR state_fingerprint <> previous_state_fingerprint;

INSERT IGNORE INTO tmp_keep_fraud_store_profile_field_snapshot_ids (id)
SELECT id
FROM (
  SELECT
    id,
    ROW_NUMBER() OVER (
      PARTITION BY store_id
      ORDER BY checked_at DESC, id DESC
    ) AS row_number_for_store
  FROM fraud_store_profile_field_snapshots
) latest
WHERE row_number_for_store = 1;

DELETE fspfs
FROM fraud_store_profile_field_snapshots fspfs
LEFT JOIN tmp_keep_fraud_store_profile_field_snapshot_ids keep_ids
  ON keep_ids.id = fspfs.id
WHERE keep_ids.id IS NULL;
SELECT ROW_COUNT() AS deleted_fraud_store_profile_field_snapshots;

SELECT 0 AS deleted_fraud_training_label_candidates;

-- 5) Result summary.
SELECT
  @cleanup_started_at AS cleanup_started_at,
  NOW() AS cleanup_finished_at;

SELECT
  'fraud_product_snapshots' AS table_name,
  @before_fraud_product_snapshots AS before_rows,
  COUNT(*) AS after_rows,
  @before_fraud_product_snapshots - COUNT(*) AS deleted_rows
FROM fraud_product_snapshots
UNION ALL
SELECT
  'fraud_store_status_snapshots',
  @before_fraud_store_status_snapshots,
  COUNT(*),
  @before_fraud_store_status_snapshots - COUNT(*)
FROM fraud_store_status_snapshots
UNION ALL
SELECT
  'fraud_store_activity_snapshots',
  @before_fraud_store_activity_snapshots,
  COUNT(*),
  @before_fraud_store_activity_snapshots - COUNT(*)
FROM fraud_store_activity_snapshots
UNION ALL
SELECT
  'fraud_store_profile_field_snapshots',
  @before_fraud_store_profile_field_snapshots,
  COUNT(*),
  @before_fraud_store_profile_field_snapshots - COUNT(*)
FROM fraud_store_profile_field_snapshots
UNION ALL
SELECT
  'fraud_training_label_candidates',
  @before_fraud_training_label_candidates,
  COUNT(*),
  @before_fraud_training_label_candidates - COUNT(*)
FROM fraud_training_label_candidates;
