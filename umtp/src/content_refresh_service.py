import os
from datetime import datetime, timedelta

try:
    from src.analysis_jobs import create_analysis_jobs_for_rules
    from src.db import get_connection
    from src.joongna_seen_products import (
        build_listing_content_snapshot,
        get_seen_product,
        update_seen_product_content_snapshot,
    )
    from src.listing_page_parser import fetch_html, parse_joongna_listing_page
    from src.search_result_enrichment import (
        load_latest_search_result,
        persist_latest_search_result_enrichment,
    )
except ModuleNotFoundError:
    from analysis_jobs import create_analysis_jobs_for_rules
    from db import get_connection
    from joongna_seen_products import (
        build_listing_content_snapshot,
        get_seen_product,
        update_seen_product_content_snapshot,
    )
    from listing_page_parser import fetch_html, parse_joongna_listing_page
    from search_result_enrichment import (
        load_latest_search_result,
        persist_latest_search_result_enrichment,
    )


FRESH_INTERVAL_MINUTES = int(os.getenv("CONTENT_REFRESH_FRESH_MINUTES", "3"))
RECENT_INTERVAL_MINUTES = int(os.getenv("CONTENT_REFRESH_RECENT_MINUTES", "20"))
OLDER_INTERVAL_MINUTES = int(os.getenv("CONTENT_REFRESH_OLDER_MINUTES", "360"))
LOOKBACK_DAYS = int(os.getenv("CONTENT_REFRESH_LOOKBACK_DAYS", "7"))


def _row_dict(row):
    if isinstance(row, dict):
        return dict(row)
    if not isinstance(row, (tuple, list)):
        return None
    keys = (
        "product_id", "search_word", "title", "price", "product_url",
        "sort_date", "first_seen_at", "last_seen_at", "last_content_checked_at",
        "last_body_hash", "last_self_check_hash",
    )
    return {key: row[index] if index < len(row) else None for index, key in enumerate(keys)}


def has_pending_analysis_jobs(cursor):
    cursor.execute(
        "SELECT 1 FROM analysis_jobs WHERE status IN ('pending', 'running') LIMIT 1"
    )
    return cursor.fetchone() is not None


def find_due_content_candidate(cursor, *, now=None):
    current = now or datetime.now()
    fresh_cutoff = current - timedelta(minutes=max(1, FRESH_INTERVAL_MINUTES))
    recent_cutoff = current - timedelta(minutes=max(1, RECENT_INTERVAL_MINUTES))
    older_cutoff = current - timedelta(minutes=max(1, OLDER_INTERVAL_MINUTES))
    lookback_cutoff = current - timedelta(days=max(1, LOOKBACK_DAYS))
    cursor.execute(
        """
        SELECT
            p.seq AS product_id,
            p.search_word,
            p.last_title AS title,
            p.last_price_krw AS price,
            p.product_url,
            p.last_sort_date AS sort_date,
            p.first_seen_at,
            p.last_seen_at,
            p.last_content_checked_at,
            p.last_body_hash,
            p.last_self_check_hash
        FROM joongna_seen_products p
        WHERE p.last_seen_at >= %s
          AND p.product_url IS NOT NULL
          AND LENGTH(TRIM(p.product_url)) > 0
          AND EXISTS (
              SELECT 1
              FROM search_results sr
              INNER JOIN search_queries sq ON sq.id = sr.search_query_id
              INNER JOIN user_fair_prices ufp
                ON LOWER(TRIM(ufp.search_keyword)) = LOWER(TRIM(sq.normalized_keyword))
              WHERE sr.product_id = CAST(p.seq AS CHAR)
                AND ufp.enabled = TRUE
                AND ufp.last_poll_requested_at IS NOT NULL
          )
          AND (
              p.last_content_checked_at IS NULL
              OR (p.first_seen_at >= DATE_SUB(%s, INTERVAL 1 HOUR)
                  AND p.last_content_checked_at <= %s)
              OR (p.first_seen_at >= DATE_SUB(%s, INTERVAL 1 DAY)
                  AND p.first_seen_at < DATE_SUB(%s, INTERVAL 1 HOUR)
                  AND p.last_content_checked_at <= %s)
              OR (p.first_seen_at < DATE_SUB(%s, INTERVAL 1 DAY)
                  AND p.last_content_checked_at <= %s)
          )
        ORDER BY
            (p.last_content_checked_at IS NULL) DESC,
            p.last_content_checked_at ASC,
            p.last_seen_at DESC
        LIMIT 1
        """,
        (
            lookback_cutoff,
            current, fresh_cutoff,
            current, current, recent_cutoff,
            current, older_cutoff,
        ),
    )
    return _row_dict(cursor.fetchone())


def load_active_targets_for_product(cursor, product_id, sort_date):
    cursor.execute(
        """
        SELECT DISTINCT
            ufp.id AS setting_id,
            ufp.user_id,
            ufp.search_keyword,
            ufp.saved_at
        FROM search_results sr
        INNER JOIN search_queries sq ON sq.id = sr.search_query_id
        INNER JOIN user_fair_prices ufp
          ON LOWER(TRIM(ufp.search_keyword)) = LOWER(TRIM(sq.normalized_keyword))
        WHERE sr.product_id = %s
          AND ufp.enabled = TRUE
          AND ufp.last_poll_requested_at IS NOT NULL
          AND (%s IS NULL OR ufp.saved_at IS NULL OR ufp.saved_at <= %s)
        ORDER BY ufp.id
        """,
        (str(product_id), sort_date, sort_date),
    )
    rows = cursor.fetchall() or []
    targets = []
    for row in rows:
        if isinstance(row, dict):
            setting_id = row.get("setting_id")
            user_id = row.get("user_id")
            search_keyword = row.get("search_keyword")
            saved_at = row.get("saved_at")
        else:
            setting_id = row[0] if len(row) > 0 else None
            user_id = row[1] if len(row) > 1 else None
            search_keyword = row[2] if len(row) > 2 else None
            saved_at = row[3] if len(row) > 3 else None
        if setting_id is None or not user_id:
            continue
        targets.append(
            {
                "setting_id": setting_id,
                "rule_id": setting_id,
                "user_id": user_id,
                "search_keyword": search_keyword,
                "saved_at": saved_at,
            }
        )
    return targets


def _content_change_reason(previous, snapshot):
    previous_body = (previous or {}).get("last_body_hash")
    current_body = (snapshot or {}).get("body_hash")
    if previous_body and current_body and previous_body != current_body:
        return "body_changed"
    previous_self_check = (previous or {}).get("last_self_check_hash")
    current_self_check = (snapshot or {}).get("self_check_hash")
    if previous_self_check and current_self_check and previous_self_check != current_self_check:
        return "self_check_changed"
    return None


def _mark_content_check_failed(product_id, error_message):
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE joongna_seen_products
            SET last_content_checked_at = CURRENT_TIMESTAMP,
                last_status = 'content_check_failed'
            WHERE seq = %s
            """,
            (product_id,),
        )
        connection.commit()
    except Exception:
        if connection is not None:
            connection.rollback()
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
    print(
        "[content_refresh] detail fetch failed "
        f"product_id={product_id}, error={error_message}"
    )


def process_next_content_refresh():
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        if has_pending_analysis_jobs(cursor):
            return {"processed": 0, "deferred": 1, "reason": "analysis_backlog"}
        candidate = find_due_content_candidate(cursor)
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    if not candidate:
        return {"processed": 0, "deferred": 0, "reason": "no_due_candidate"}

    product_id = candidate.get("product_id")
    try:
        page = parse_joongna_listing_page(fetch_html(candidate.get("product_url")))
    except Exception as exc:
        _mark_content_check_failed(product_id, str(exc))
        return {"processed": 1, "failed": 1, "product_id": product_id, "reason": str(exc)}

    title = page.get("title") or candidate.get("title")
    price = page.get("listing_price_krw")
    if price is None:
        price = candidate.get("price")
    body_text = page.get("description")
    self_check_fields = page.get("self_check_fields") or {}
    snapshot = build_listing_content_snapshot(
        title=title,
        price_krw=price,
        body_text=body_text,
        self_check_fields=self_check_fields,
    )

    connection = None
    cursor = None
    targets = []
    seller_profile = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        previous = get_seen_product(cursor, product_id) or {}
        reason = _content_change_reason(previous, snapshot)
        latest_search_result = load_latest_search_result(cursor, product_id) or {}
        store_seq = latest_search_result.get("seller_store_seq")
        if store_seq is not None:
            try:
                try:
                    from src.joongna_polling_service import resolve_store_profile_for_store_seq
                except ModuleNotFoundError:
                    from joongna_polling_service import resolve_store_profile_for_store_seq
                seller_profile = resolve_store_profile_for_store_seq(cursor, store_seq)
            except Exception as exc:
                print(
                    "[content_refresh] seller profile refresh skipped "
                    f"storeSeq={store_seq}, error={exc}"
                )
        persist_latest_search_result_enrichment(
            cursor,
            product_id,
            body_text=body_text,
            self_check_fields=self_check_fields,
            seller_profile=seller_profile,
        )
        update_seen_product_content_snapshot(
            cursor,
            product_id,
            title=title,
            price_krw=price,
            body_text=body_text,
            self_check_fields=self_check_fields,
            changed_reason=reason,
        )
        if reason:
            targets = load_active_targets_for_product(
                cursor,
                product_id,
                candidate.get("sort_date"),
            )
        connection.commit()
    except Exception:
        if connection is not None:
            connection.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    enqueue_result = None
    if reason and targets:
        product = {
            "source": "joongna",
            "product_id": product_id,
            "product_url": candidate.get("product_url"),
            "title": title,
            "price": price,
            "search_keyword": candidate.get("search_word"),
            "search_word": candidate.get("search_word"),
            "sort_date": candidate.get("sort_date"),
            "body_text": body_text,
            "self_check_fields": self_check_fields,
            "body_hash": snapshot.get("body_hash"),
            "self_check_hash": snapshot.get("self_check_hash"),
            "content_revision_hash": snapshot.get("content_revision_hash"),
            "change_fingerprint": snapshot.get("content_revision_hash"),
        }
        enqueue_result = create_analysis_jobs_for_rules(product, targets, reason)

    return {
        "processed": 1,
        "failed": 0,
        "product_id": product_id,
        "change_reason": reason,
        "target_count": len(targets),
        "analysis_jobs_created": len((enqueue_result or {}).get("created_jobs") or []),
    }
