import argparse
import csv
import os
import time
from typing import Any, Dict, Iterable, List, Optional

from bs4 import BeautifulSoup

try:
    from src.analysis_log import _insert_url_analysis_log
    from src.db import get_connection
    from src.listing_page_parser import fetch_html, find_price_text, parse_price_to_int
except ModuleNotFoundError:
    from analysis_log import _insert_url_analysis_log
    from db import get_connection
    from listing_page_parser import fetch_html, find_price_text, parse_price_to_int


DEFAULT_INPUT_PATH = os.path.join(
    "data",
    "fraud_probability",
    "training_features_v2_step1.csv",
)
DEFAULT_FAILURES_PATH = os.path.join(
    "data",
    "fraud_probability",
    "body_text_backfill_failures.csv",
)
DEFAULT_USER_ID = "fraud-body-backfill"
SOURCE_NAME = "joongna"
SUCCESS_STATUS = "body_backfill"
FAILURE_STATUS = "body_backfill_failed"
REASON = "fraud_probability_v2_body_text_backfill"


def _normalize_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    cleaned = str(value).strip()
    return cleaned or None


def _safe_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _missing_body_product_ids(input_path: str) -> List[str]:
    product_ids: List[str] = []
    with open(input_path, newline="", encoding="utf-8") as input_file:
        reader = csv.DictReader(input_file)
        for row in reader:
            product_id = _normalize_text(row.get("product_id"))
            body_text = _normalize_text(row.get("body_text"))
            if product_id and body_text is None:
                product_ids.append(product_id)
    return product_ids


def _fetch_target_rows(cursor, product_ids: Iterable[str]) -> List[Dict[str, Any]]:
    unique_product_ids = list(dict.fromkeys(product_ids))
    if not unique_product_ids:
        return []

    placeholders = ",".join(["%s"] * len(unique_product_ids))
    cursor.execute(
        f"""
        WITH first_search_result AS (
          SELECT *
          FROM (
            SELECT
              sr.*,
              ROW_NUMBER() OVER (
                PARTITION BY CAST(sr.product_id AS CHAR)
                ORDER BY sr.fetched_at ASC, sr.id ASC
              ) AS rn
            FROM search_results sr
            WHERE CAST(sr.product_id AS CHAR) IN ({placeholders})
          ) ranked
          WHERE rn = 1
        )
        SELECT
          ids.product_id,
          COALESCE(fsr.url, jsp.product_url, CONCAT('https://web.joongna.com/product/', ids.product_id)) AS url,
          COALESCE(fsr.title, jsp.title, jsp.last_title) AS fallback_title,
          COALESCE(fsr.price, jsp.price, jsp.last_price_krw) AS fallback_price_krw
        FROM (
          SELECT %s AS product_id
        ) ids
        LEFT JOIN first_search_result fsr
          ON CAST(fsr.product_id AS CHAR) = ids.product_id
        LEFT JOIN joongna_seen_products jsp
          ON CAST(jsp.seq AS CHAR) = ids.product_id
        """,
        tuple(unique_product_ids) + (unique_product_ids[0],),
    )
    first_row = cursor.fetchall() or []
    if len(unique_product_ids) == 1:
        return first_row

    # MySQL does not support binding a VALUES table portably across the local
    # connector versions in this project, so fetch remaining ids individually.
    rows_by_product_id = {str(row["product_id"]): row for row in first_row}
    for product_id in unique_product_ids[1:]:
        cursor.execute(
            """
            SELECT
              %s AS product_id,
              COALESCE(fsr.url, jsp.product_url, CONCAT('https://web.joongna.com/product/', %s)) AS url,
              COALESCE(fsr.title, jsp.title, jsp.last_title) AS fallback_title,
              COALESCE(fsr.price, jsp.price, jsp.last_price_krw) AS fallback_price_krw
            FROM (SELECT 1) seed
            LEFT JOIN (
              SELECT *
              FROM search_results
              WHERE CAST(product_id AS CHAR) = %s
              ORDER BY fetched_at ASC, id ASC
              LIMIT 1
            ) fsr ON TRUE
            LEFT JOIN joongna_seen_products jsp
              ON CAST(jsp.seq AS CHAR) = %s
            """,
            (product_id, product_id, product_id, product_id),
        )
        row = cursor.fetchone()
        if row:
            rows_by_product_id[product_id] = row

    return [rows_by_product_id[product_id] for product_id in unique_product_ids if product_id in rows_by_product_id]


def _extract_listing_text(html: str, fallback_title: Any = None, fallback_price_krw: Any = None) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("meta", attrs={"name": "twitter:title"})
    title = _normalize_text(title_tag.get("content") if title_tag else None)
    if title is None:
        title = _normalize_text(fallback_title)

    description_tag = soup.find("meta", attrs={"name": "twitter:description"})
    body_text = _normalize_text(description_tag.get("content") if description_tag else None)

    listing_price_krw = None
    price_text = find_price_text(soup)
    if price_text:
        try:
            listing_price_krw = parse_price_to_int(price_text)
        except ValueError:
            listing_price_krw = None
    if listing_price_krw is None:
        listing_price_krw = _safe_int(fallback_price_krw)

    return {
        "title": title,
        "body_text": body_text,
        "listing_price_krw": listing_price_krw,
    }


def _write_failures(output_path: str, failures: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fieldnames = ["product_id", "url", "reason"]
    with open(output_path, "w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(failures)


def backfill_body_text(
    *,
    input_path: str = DEFAULT_INPUT_PATH,
    failures_path: str = DEFAULT_FAILURES_PATH,
    user_id: str = DEFAULT_USER_ID,
    product_id: Optional[str] = None,
    limit: Optional[int] = None,
    sleep_seconds: float = 0.0,
    dry_run: bool = False,
) -> Dict[str, Any]:
    product_ids = [product_id] if product_id else _missing_body_product_ids(input_path)
    if limit is not None:
        product_ids = product_ids[:limit]

    connection = get_connection()
    successes: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    try:
        cursor = connection.cursor(dictionary=True)
        target_rows = _fetch_target_rows(cursor, product_ids)
        for index, row in enumerate(target_rows, start=1):
            current_product_id = _normalize_text(row.get("product_id"))
            url = _normalize_text(row.get("url"))
            if current_product_id is None or url is None:
                failures.append(
                    {
                        "product_id": current_product_id or "",
                        "url": url or "",
                        "reason": "missing_product_id_or_url",
                    }
                )
                continue

            try:
                html = fetch_html(url)
                parsed = _extract_listing_text(
                    html,
                    fallback_title=row.get("fallback_title"),
                    fallback_price_krw=row.get("fallback_price_krw"),
                )
                if parsed["body_text"] is None:
                    raise RuntimeError("missing_twitter_description")

                if not dry_run:
                    _insert_url_analysis_log(
                        cursor,
                        user_id=user_id,
                        url=url,
                        source=SOURCE_NAME,
                        title=parsed["title"],
                        body_text=parsed["body_text"],
                        listing_price_krw=parsed["listing_price_krw"],
                        product_type=None,
                        chip=None,
                        screen_inch=None,
                        ram_gb=None,
                        ssd_gb=None,
                        fair_price_krw=None,
                        diff_ratio=None,
                        is_alert_target=None,
                        status=SUCCESS_STATUS,
                        reason=REASON,
                    )
                    connection.commit()

                successes.append(
                    {
                        "product_id": current_product_id,
                        "url": url,
                        "body_len": len(parsed["body_text"]),
                    }
                )
                print(
                    f"[{index}/{len(target_rows)}] saved product_id={current_product_id} "
                    f"body_len={len(parsed['body_text'])} url={url}"
                )
            except Exception as exc:
                if not dry_run:
                    try:
                        _insert_url_analysis_log(
                            cursor,
                            user_id=user_id,
                            url=url,
                            source=SOURCE_NAME,
                            title=row.get("fallback_title"),
                            body_text=None,
                            listing_price_krw=_safe_int(row.get("fallback_price_krw")),
                            product_type=None,
                            chip=None,
                            screen_inch=None,
                            ram_gb=None,
                            ssd_gb=None,
                            fair_price_krw=None,
                            diff_ratio=None,
                            is_alert_target=None,
                            status=FAILURE_STATUS,
                            reason=str(exc)[:255],
                        )
                        connection.commit()
                    except Exception:
                        connection.rollback()
                failures.append(
                    {
                        "product_id": current_product_id,
                        "url": url,
                        "reason": str(exc),
                    }
                )
                print(f"[{index}/{len(target_rows)}] failed product_id={current_product_id} reason={exc}")

            if sleep_seconds > 0 and index < len(target_rows):
                time.sleep(sleep_seconds)
    finally:
        if "cursor" in locals():
            cursor.close()
        if connection.is_connected():
            connection.close()

    _write_failures(failures_path, failures)
    return {
        "target_count": len(product_ids),
        "success_count": len(successes),
        "failure_count": len(failures),
        "failures_path": failures_path,
        "dry_run": dry_run,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Backfill body_text for fraud probability training rows")
    parser.add_argument("--input", default=DEFAULT_INPUT_PATH)
    parser.add_argument("--failures-output", default=DEFAULT_FAILURES_PATH)
    parser.add_argument("--user-id", default=DEFAULT_USER_ID)
    parser.add_argument("--product-id")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    result = backfill_body_text(
        input_path=args.input,
        failures_path=args.failures_output,
        user_id=args.user_id,
        product_id=args.product_id,
        limit=args.limit,
        sleep_seconds=args.sleep_seconds,
        dry_run=args.dry_run,
    )
    print(f"targets={result['target_count']}")
    print(f"successes={result['success_count']}")
    print(f"failures={result['failure_count']}")
    print(f"failures_path={result['failures_path']}")


if __name__ == "__main__":
    main()
