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
  ) ranked
  WHERE rn = 1
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
    NULLIF(TRIM(ful.body_text), ''),
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
