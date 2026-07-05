import argparse
import csv
import os
from typing import Any, Dict, List

try:
    from src.db import get_connection
except ModuleNotFoundError:
    from db import get_connection


DEFAULT_OUTPUT_PATH = os.path.join(
    "data",
    "fraud_probability",
    "training_features.csv",
)

TRAINING_FEATURE_SQL = """
WITH labeled AS (
  SELECT
    product_id,
    store_id,
    listing_sort_date,
    discovered_at,
    label
  FROM fraud_training_label_candidates
  WHERE label IS NOT NULL
),
first_search_result AS (
  SELECT *
  FROM (
    SELECT
      sr.*,
      ROW_NUMBER() OVER (
        PARTITION BY CAST(sr.product_id AS CHAR)
        ORDER BY sr.fetched_at ASC, sr.id ASC
      ) AS rn
    FROM search_results sr
    JOIN labeled l
      ON CAST(sr.product_id AS CHAR) = l.product_id
  ) ranked
  WHERE rn = 1
),
latest_activity AS (
  SELECT *
  FROM (
    SELECT
      l.product_id AS labeled_product_id,
      fsa.posts_last_1h,
      fsa.posts_last_6h,
      fsa.posts_last_24h,
      fsa.posts_last_7d,
      fsa.visible_product_count,
      fsa.has_default_profile_image,
      fsa.review_count,
      fsa.safe_trade_count,
      fsa.trust_score,
      fsa.reliability_score,
      fsa.activity_score,
      fsa.notified_score,
      fsa.visit_today_count,
      fsa.visit_total_count,
      ROW_NUMBER() OVER (
        PARTITION BY l.product_id
        ORDER BY fsa.checked_at DESC, fsa.id DESC
      ) AS rn
    FROM labeled l
    JOIN first_search_result fsr
      ON CAST(fsr.product_id AS CHAR) = l.product_id
    LEFT JOIN fraud_store_activity_snapshots fsa
      ON fsa.store_id = l.store_id
     AND fsa.checked_at <= DATE_ADD(fsr.fetched_at, INTERVAL 30 MINUTE)
  ) ranked
  WHERE rn = 1
),
latest_profile AS (
  SELECT *
  FROM (
    SELECT
      l.product_id AS labeled_product_id,
      fsp.review_count AS profile_review_count,
      fsp.safe_trade_count AS profile_safe_trade_count,
      fsp.trust_score AS profile_trust_score,
      fsp.reliability_score AS profile_reliability_score,
      fsp.activity_score AS profile_activity_score,
      fsp.notified_score AS profile_notified_score,
      fsp.visit_today_count AS profile_visit_today_count,
      fsp.visit_total_count AS profile_visit_total_count,
      fsp.is_official_account AS profile_is_official_account,
      ROW_NUMBER() OVER (
        PARTITION BY l.product_id
        ORDER BY fsp.checked_at DESC, fsp.id DESC
      ) AS rn
    FROM labeled l
    JOIN first_search_result fsr
      ON CAST(fsr.product_id AS CHAR) = l.product_id
    LEFT JOIN fraud_store_profile_field_snapshots fsp
      ON fsp.store_id = l.store_id
     AND fsp.checked_at <= DATE_ADD(fsr.fetched_at, INTERVAL 30 MINUTE)
  ) ranked
  WHERE rn = 1
),
first_alert AS (
  SELECT *
  FROM (
    SELECT
      ae.*,
      ROW_NUMBER() OVER (
        PARTITION BY CAST(ae.product_id AS CHAR)
        ORDER BY ae.created_at ASC, ae.id ASC
      ) AS rn
    FROM alert_events ae
    JOIN labeled l
      ON CAST(ae.product_id AS CHAR) = l.product_id
  ) ranked
  WHERE rn = 1
),
first_url_log AS (
  SELECT *
  FROM (
    SELECT
      l.product_id AS labeled_product_id,
      ual.title,
      ual.body_text,
      ROW_NUMBER() OVER (
        PARTITION BY l.product_id
        ORDER BY ual.created_at ASC, ual.id ASC
      ) AS rn
    FROM labeled l
    JOIN first_search_result fsr
      ON CAST(fsr.product_id AS CHAR) = l.product_id
    LEFT JOIN first_alert fa
      ON CAST(fa.product_id AS CHAR) = l.product_id
    JOIN url_analysis_logs ual
      ON ual.url = fsr.url
     AND ual.created_at <= DATE_ADD(
       COALESCE(fa.created_at, l.discovered_at, fsr.fetched_at, l.listing_sort_date),
       INTERVAL 30 MINUTE
     )
     AND NULLIF(TRIM(ual.body_text), '') IS NOT NULL
  ) ranked
  WHERE rn = 1
),
first_url_log_any_time AS (
  SELECT *
  FROM (
    SELECT
      l.product_id AS labeled_product_id,
      ual.title,
      ual.body_text,
      ROW_NUMBER() OVER (
        PARTITION BY l.product_id
        ORDER BY ual.created_at ASC, ual.id ASC
      ) AS rn
    FROM labeled l
    JOIN first_search_result fsr
      ON CAST(fsr.product_id AS CHAR) = l.product_id
    JOIN url_analysis_logs ual
      ON ual.url = fsr.url
     AND NULLIF(TRIM(ual.body_text), '') IS NOT NULL
  ) ranked
  WHERE rn = 1
),
first_alert_archive AS (
  SELECT *
  FROM (
    SELECT
      l.product_id AS labeled_product_id,
      area.alert_body_text,
      area.alert_body_excerpt,
      ROW_NUMBER() OVER (
        PARTITION BY l.product_id
        ORDER BY area.created_at ASC, area.id ASC
      ) AS rn
    FROM labeled l
    JOIN alert_read_archive_events area
      ON CAST(area.alert_product_id AS CHAR) = l.product_id
     AND NULLIF(TRIM(COALESCE(area.alert_body_text, area.alert_body_excerpt, '')), '') IS NOT NULL
  ) ranked
  WHERE rn = 1
),
first_listing_result_by_alert_job AS (
  SELECT *
  FROM (
    SELECT
      l.product_id AS labeled_product_id,
      lar.body_text,
      ROW_NUMBER() OVER (
        PARTITION BY l.product_id
        ORDER BY lar.created_at ASC, lar.id ASC
      ) AS rn
    FROM labeled l
    JOIN first_alert fa
      ON CAST(fa.product_id AS CHAR) = l.product_id
    JOIN listing_analysis_results lar
      ON lar.analysis_job_id = fa.analysis_job_id
     AND NULLIF(TRIM(lar.body_text), '') IS NOT NULL
  ) ranked
  WHERE rn = 1
),
first_listing_result_by_analysis_job AS (
  SELECT *
  FROM (
    SELECT
      l.product_id AS labeled_product_id,
      lar.body_text,
      ROW_NUMBER() OVER (
        PARTITION BY l.product_id
        ORDER BY lar.created_at ASC, lar.id ASC
      ) AS rn
    FROM labeled l
    JOIN analysis_jobs aj
      ON CAST(aj.product_id AS CHAR) = l.product_id
    JOIN listing_analysis_results lar
      ON lar.analysis_job_id = aj.id
     AND NULLIF(TRIM(lar.body_text), '') IS NOT NULL
  ) ranked
  WHERE rn = 1
),
first_listing_result_by_title_price AS (
  SELECT *
  FROM (
    SELECT
      l.product_id AS labeled_product_id,
      lar.body_text,
      ROW_NUMBER() OVER (
        PARTITION BY l.product_id
        ORDER BY lar.created_at ASC, lar.id ASC
      ) AS rn
    FROM labeled l
    JOIN first_search_result fsr
      ON CAST(fsr.product_id AS CHAR) = l.product_id
    JOIN listing_analysis_results lar
      ON lar.title = fsr.title
     AND lar.listing_price_krw = fsr.price
     AND NULLIF(TRIM(lar.body_text), '') IS NOT NULL
  ) ranked
  WHERE rn = 1
),
seller_search_history AS (
  SELECT
    l.product_id AS labeled_product_id,
    COUNT(srh.id) AS seller_search_result_count_before,
    COUNT(
      CASE
        WHEN srh.fetched_at >= DATE_SUB(fsr.fetched_at, INTERVAL 7 DAY)
          THEN srh.id
        ELSE NULL
      END
    ) AS seller_search_result_count_7d,
    COUNT(DISTINCT CAST(srh.product_id AS CHAR)) AS seller_seen_product_count_before,
    COUNT(
      DISTINCT CASE
        WHEN srh.fetched_at >= DATE_SUB(fsr.fetched_at, INTERVAL 24 HOUR)
          THEN CAST(srh.product_id AS CHAR)
        ELSE NULL
      END
    ) AS seller_seen_product_count_24h,
    COUNT(
      DISTINCT CASE
        WHEN srh.fetched_at >= DATE_SUB(fsr.fetched_at, INTERVAL 7 DAY)
          THEN CAST(srh.product_id AS CHAR)
        ELSE NULL
      END
    ) AS seller_seen_product_count_7d,
    TIMESTAMPDIFF(HOUR, MIN(srh.fetched_at), fsr.fetched_at) AS seller_history_age_hours,
    AVG(
      CASE
        WHEN srh.fetched_at >= DATE_SUB(fsr.fetched_at, INTERVAL 7 DAY)
          THEN srh.price
        ELSE NULL
      END
    ) AS seller_avg_price_7d,
    MIN(
      CASE
        WHEN srh.fetched_at >= DATE_SUB(fsr.fetched_at, INTERVAL 7 DAY)
          THEN srh.price
        ELSE NULL
      END
    ) AS seller_min_price_7d,
    MAX(
      CASE
        WHEN srh.fetched_at >= DATE_SUB(fsr.fetched_at, INTERVAL 7 DAY)
          THEN srh.price
        ELSE NULL
      END
    ) AS seller_max_price_7d
  FROM labeled l
  JOIN first_search_result fsr
    ON CAST(fsr.product_id AS CHAR) = l.product_id
  LEFT JOIN search_results srh
    ON CAST(srh.seller_store_seq AS CHAR) = l.store_id
   AND CAST(srh.product_id AS CHAR) <> l.product_id
   AND srh.fetched_at < fsr.fetched_at
  GROUP BY l.product_id, fsr.fetched_at
),
seller_snapshot_history AS (
  SELECT
    l.product_id AS labeled_product_id,
    COUNT(fph.id) AS seller_product_snapshot_count_before,
    COUNT(
      CASE
        WHEN fph.observed_at >= DATE_SUB(fsr.fetched_at, INTERVAL 7 DAY)
          THEN fph.id
        ELSE NULL
      END
    ) AS seller_product_snapshot_count_7d,
    SUM(
      CASE
        WHEN fph.observed_at >= DATE_SUB(fsr.fetched_at, INTERVAL 7 DAY)
         AND fph.snapshot_reason = 'price_changed'
          THEN 1
        ELSE 0
      END
    ) AS seller_price_change_count_7d,
    SUM(
      CASE
        WHEN fph.observed_at >= DATE_SUB(fsr.fetched_at, INTERVAL 7 DAY)
         AND fph.snapshot_reason = 'content_changed'
          THEN 1
        ELSE 0
      END
    ) AS seller_content_change_count_7d
  FROM labeled l
  JOIN first_search_result fsr
    ON CAST(fsr.product_id AS CHAR) = l.product_id
  LEFT JOIN fraud_product_snapshots fph
    ON fph.store_id = l.store_id
   AND fph.product_id <> l.product_id
   AND fph.observed_at < fsr.fetched_at
  GROUP BY l.product_id
),
seller_alert_history AS (
  SELECT
    l.product_id AS labeled_product_id,
    COUNT(aeh.id) AS seller_alert_count_before,
    COUNT(
      CASE
        WHEN aeh.created_at >= DATE_SUB(fsr.fetched_at, INTERVAL 30 DAY)
          THEN aeh.id
        ELSE NULL
      END
    ) AS seller_alert_count_30d,
    COUNT(
      DISTINCT CASE
        WHEN aeh.created_at >= DATE_SUB(fsr.fetched_at, INTERVAL 30 DAY)
          THEN CAST(aeh.product_id AS CHAR)
        ELSE NULL
      END
    ) AS seller_alert_product_count_30d
  FROM labeled l
  JOIN first_search_result fsr
    ON CAST(fsr.product_id AS CHAR) = l.product_id
  LEFT JOIN alert_events aeh
    ON CAST(aeh.seller_store_seq AS CHAR) = l.store_id
   AND (aeh.product_id IS NULL OR CAST(aeh.product_id AS CHAR) <> l.product_id)
   AND aeh.created_at < fsr.fetched_at
  GROUP BY l.product_id
),
seller_store_name_history AS (
  SELECT
    l.product_id AS labeled_product_id,
    COUNT(jnc.id) AS seller_store_name_change_count_before,
    COUNT(
      CASE
        WHEN jnc.changed_at >= DATE_SUB(fsr.fetched_at, INTERVAL 30 DAY)
          THEN jnc.id
        ELSE NULL
      END
    ) AS seller_store_name_change_count_30d
  FROM labeled l
  JOIN first_search_result fsr
    ON CAST(fsr.product_id AS CHAR) = l.product_id
  LEFT JOIN joongna_store_name_changes jnc
    ON CAST(jnc.store_seq AS CHAR) = l.store_id
   AND jnc.changed_at < fsr.fetched_at
  GROUP BY l.product_id
)
SELECT
  l.label,
  l.product_id,
  l.store_id,

  COALESCE(
    NULLIF(TRIM(fa.title), ''),
    NULLIF(TRIM(fsr.title), ''),
    NULLIF(TRIM(ful.title), ''),
    ''
  ) AS title_text,
  COALESCE(
    NULLIF(TRIM(fa.body_text), ''),
    NULLIF(TRIM(fa.body_excerpt), ''),
    NULLIF(TRIM(fsr.body_text), ''),
    NULLIF(TRIM(ful.body_text), ''),
    NULLIF(TRIM(faa.alert_body_text), ''),
    NULLIF(TRIM(faa.alert_body_excerpt), ''),
    NULLIF(TRIM(flj.body_text), ''),
    NULLIF(TRIM(fla.body_text), ''),
    NULLIF(TRIM(fua.body_text), ''),
    NULLIF(TRIM(flt.body_text), ''),
    ''
  ) AS body_text,

  fsr.price AS price_krw,
  CHAR_LENGTH(COALESCE(fsr.title, '')) AS title_len,
  HOUR(fsr.sort_date) AS sort_hour,
  DAYOFWEEK(fsr.sort_date) AS sort_dayofweek,
  CASE
    WHEN fsr.seller_profile_image_url IS NULL OR fsr.seller_profile_image_url = '' THEN 0
    ELSE 1
  END AS has_profile_image,
  CHAR_LENGTH(COALESCE(fsr.seller_store_name, '')) AS store_name_len,
  fsr.seller_review_count,

  CASE WHEN la.labeled_product_id IS NULL THEN 0 ELSE 1 END AS has_activity_snapshot,
  la.posts_last_1h,
  la.posts_last_6h,
  la.posts_last_24h,
  la.posts_last_7d,
  la.visible_product_count,
  la.has_default_profile_image,
  la.review_count AS activity_review_count,
  la.safe_trade_count,
  la.trust_score,
  la.reliability_score,
  la.activity_score,
  la.notified_score,
  la.visit_today_count,
  la.visit_total_count,

  CASE WHEN lp.labeled_product_id IS NULL THEN 0 ELSE 1 END AS has_profile_snapshot,
  lp.profile_review_count,
  lp.profile_safe_trade_count,
  lp.profile_trust_score,
  lp.profile_reliability_score,
  lp.profile_activity_score,
  lp.profile_notified_score,
  lp.profile_visit_today_count,
  lp.profile_visit_total_count,
  lp.profile_is_official_account,

  CASE
    WHEN COALESCE(ssh.seller_seen_product_count_before, 0) > 0
      OR COALESCE(sph.seller_product_snapshot_count_before, 0) > 0
      OR COALESCE(sah.seller_alert_count_before, 0) > 0
      OR COALESCE(ssnh.seller_store_name_change_count_before, 0) > 0
      THEN 1
    ELSE 0
  END AS has_seller_history,
  COALESCE(ssh.seller_search_result_count_before, 0) AS seller_search_result_count_before,
  COALESCE(ssh.seller_search_result_count_7d, 0) AS seller_search_result_count_7d,
  COALESCE(ssh.seller_seen_product_count_before, 0) AS seller_seen_product_count_before,
  COALESCE(ssh.seller_seen_product_count_24h, 0) AS seller_seen_product_count_24h,
  COALESCE(ssh.seller_seen_product_count_7d, 0) AS seller_seen_product_count_7d,
  ssh.seller_history_age_hours,
  ssh.seller_avg_price_7d,
  ssh.seller_min_price_7d,
  ssh.seller_max_price_7d,
  COALESCE(sph.seller_product_snapshot_count_before, 0) AS seller_product_snapshot_count_before,
  COALESCE(sph.seller_product_snapshot_count_7d, 0) AS seller_product_snapshot_count_7d,
  COALESCE(sph.seller_price_change_count_7d, 0) AS seller_price_change_count_7d,
  COALESCE(sph.seller_content_change_count_7d, 0) AS seller_content_change_count_7d,
  COALESCE(sah.seller_alert_count_before, 0) AS seller_alert_count_before,
  COALESCE(sah.seller_alert_count_30d, 0) AS seller_alert_count_30d,
  COALESCE(sah.seller_alert_product_count_30d, 0) AS seller_alert_product_count_30d,
  COALESCE(ssnh.seller_store_name_change_count_before, 0) AS seller_store_name_change_count_before,
  COALESCE(ssnh.seller_store_name_change_count_30d, 0) AS seller_store_name_change_count_30d,

  fa.drop_rate_percent,
  fa.risk_score,
  COALESCE(fa.risk_level, 'unknown') AS risk_level,
  COALESCE(fa.trade_type, 'unknown') AS trade_type,
  COALESCE(fa.is_exchange_post, 0) AS is_exchange_post,
  CASE
    WHEN fa.risk_keywords IS NOT NULL AND JSON_VALID(fa.risk_keywords)
      THEN JSON_LENGTH(fa.risk_keywords)
    ELSE 0
  END AS risk_keyword_count
FROM labeled l
JOIN first_search_result fsr
  ON CAST(fsr.product_id AS CHAR) = l.product_id
LEFT JOIN latest_activity la
  ON la.labeled_product_id = l.product_id
LEFT JOIN latest_profile lp
  ON lp.labeled_product_id = l.product_id
LEFT JOIN first_alert fa
  ON CAST(fa.product_id AS CHAR) = l.product_id
LEFT JOIN first_url_log ful
  ON ful.labeled_product_id = l.product_id
LEFT JOIN first_url_log_any_time fua
  ON fua.labeled_product_id = l.product_id
LEFT JOIN first_alert_archive faa
  ON faa.labeled_product_id = l.product_id
LEFT JOIN first_listing_result_by_alert_job flj
  ON flj.labeled_product_id = l.product_id
LEFT JOIN first_listing_result_by_analysis_job fla
  ON fla.labeled_product_id = l.product_id
LEFT JOIN first_listing_result_by_title_price flt
  ON flt.labeled_product_id = l.product_id
LEFT JOIN seller_search_history ssh
  ON ssh.labeled_product_id = l.product_id
LEFT JOIN seller_snapshot_history sph
  ON sph.labeled_product_id = l.product_id
LEFT JOIN seller_alert_history sah
  ON sah.labeled_product_id = l.product_id
LEFT JOIN seller_store_name_history ssnh
  ON ssnh.labeled_product_id = l.product_id
ORDER BY l.listing_sort_date ASC
"""


def fetch_training_feature_rows() -> List[Dict[str, Any]]:
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(TRAINING_FEATURE_SQL)
        return cursor.fetchall() or []
    finally:
        if "cursor" in locals():
            cursor.close()
        if connection.is_connected():
            connection.close()


def write_training_features_csv(output_path: str = DEFAULT_OUTPUT_PATH) -> Dict[str, Any]:
    rows = fetch_training_feature_rows()
    if not rows:
        raise RuntimeError("fraud probability training feature rows are empty")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fieldnames = list(rows[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return {
        "output_path": output_path,
        "row_count": len(rows),
        "column_count": len(fieldnames),
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Export fraud probability training features")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH)
    return parser.parse_args()


def main():
    args = parse_args()
    result = write_training_features_csv(args.output)
    print(f"saved={result['output_path']}")
    print(f"rows={result['row_count']}")
    print(f"columns={result['column_count']}")


if __name__ == "__main__":
    main()
