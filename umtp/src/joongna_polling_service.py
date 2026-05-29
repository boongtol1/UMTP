from datetime import datetime, timedelta, timezone
import hashlib
import json

try:
    from src.db import get_connection
    from src.joongna_search_client import fetch_joongna_store_profile, search_joongna_products
    from src.joongna_seen_products import (
        detect_listing_change,
        get_seen_product,
        should_analyze_listing,
        upsert_seen_product_observation,
    )
    from src.listing_analysis_pipeline import (
        enqueue_analysis_for_product,
    )
    from src.search_keyword_utils import dedupe_keywords_keep_order, normalize_search_keyword
    from src.user_settings_service import (
        get_due_user_fair_price_polling_targets as get_due_watch_rules,
        mark_user_fair_price_polled as mark_watch_rule_polled,
    )
except ModuleNotFoundError:
    from db import get_connection
    from joongna_search_client import fetch_joongna_store_profile, search_joongna_products
    from joongna_seen_products import (
        detect_listing_change,
        get_seen_product,
        should_analyze_listing,
        upsert_seen_product_observation,
    )
    from listing_analysis_pipeline import (
        enqueue_analysis_for_product,
    )
    from search_keyword_utils import dedupe_keywords_keep_order, normalize_search_keyword
    from user_settings_service import (
        get_due_user_fair_price_polling_targets as get_due_watch_rules,
        mark_user_fair_price_polled as mark_watch_rule_polled,
    )


STORE_PROFILE_RETRY_MINUTES = 30
STORE_PROFILE_SUCCESS_TTL_HOURS = 24


def _normalize_search_words(search_words):
    if not search_words:
        return []

    return dedupe_keywords_keep_order(search_words)


def _normalize_optional_user_id(user_id):
    if not isinstance(user_id, str):
        return None
    cleaned = user_id.strip()
    return cleaned or None


def _normalize_source(source):
    if isinstance(source, str):
        cleaned = source.strip().lower()
        if cleaned:
            return cleaned
    return "joongna"


def parse_sort_date(item):
    if not isinstance(item, dict):
        return None

    raw_value = item.get("sort_date")
    if raw_value is None:
        raw_value = item.get("sortDate")
    if raw_value is None:
        return None

    if isinstance(raw_value, str):
        cleaned = raw_value.strip()
    else:
        cleaned = str(raw_value).strip()

    return cleaned or None


def _coerce_datetime(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        parsed = value
    else:
        if isinstance(value, str):
            text = value.strip()
        else:
            text = str(value).strip()

        if not text:
            return None

        parsed = None
        candidate = text.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            pass

        if parsed is None:
            for date_format in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y/%m/%d %H:%M:%S",
                "%Y/%m/%d %H:%M",
            ):
                try:
                    parsed = datetime.strptime(text, date_format)
                    break
                except ValueError:
                    continue

        if parsed is None:
            return None

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)

    return parsed.replace(microsecond=0)


def _build_poll_stats(search_words):
    return {
        "search_words": search_words,
        "polling_group_count": 0,
        "external_api_calls": 0,
        "matched_watch_rules": 0,
        "created_alert_count": 0,
        "fetched_count": 0,
        "new_count": 0,
        "changed_count": 0,
        "unchanged_skipped_count": 0,
        "unchanged_backfill_match_count": 0,
        "unchanged_backfill_target_count": 0,
        "analyzed_count": 0,
        "alert_created_count": 0,
        "fetched_items": 0,
        "new_items": 0,
        "skipped_no_seq": 0,
        "skipped_seen": 0,
        "search_errors": 0,
        "db_errors": 0,
        "analysis_success": 0,
        "analysis_duplicate": 0,
        "analysis_failed": 0,
        "settings_due": 0,
        "settings_marked": 0,
        "analysis_jobs_created": 0,
        "analysis_jobs_skipped_duplicate": 0,
        "skipped_before_saved_at": 0,
        "analysis_jobs_processed": 0,
        "analysis_jobs_process_failed": 0,
        "search_results_saved": 0,
        "search_results_skipped_unchanged": 0,
        "search_results_save_errors": 0,
    }


def _build_observed_product(search_word, item):
    seller_store_seq = _safe_int(
        item.get("seller_store_seq") or item.get("store_seq") or item.get("storeSeq")
    )
    return {
        "product_id": item.get("product_id") or item.get("seq"),
        "seq": item.get("seq"),
        "search_word": search_word,
        "search_keyword": search_word,
        "title": item.get("title"),
        "price": item.get("price"),
        "product_url": item.get("product_url"),
        "image_url": item.get("image_url"),
        "sort_date": parse_sort_date(item),
        "refresh_key": item.get("refresh_key"),
        "body_text": item.get("body_text") or item.get("description") or item.get("content"),
        "self_check_fields": item.get("self_check_fields") if isinstance(item.get("self_check_fields"), dict) else None,
        "body_hash": item.get("body_hash") or item.get("content_hash"),
        "self_check_hash": item.get("self_check_hash"),
        "content_revision_hash": item.get("content_revision_hash"),
        "seller_store_seq": seller_store_seq,
        "seller_store_name": _safe_text(item.get("seller_store_name")),
        "seller_profile_image_url": _safe_text(item.get("seller_profile_image_url")),
        "seller_store_level": _safe_text(item.get("seller_store_level")),
        "seller_trust_score": _safe_int(item.get("seller_trust_score")),
        "seller_review_count": _safe_int(item.get("seller_review_count")),
    }


def _safe_int(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    cleaned = str(value).strip()
    return cleaned or None


def _safe_json_dumps(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except Exception:
        return "{}"


def _is_unknown_column_error(exc):
    lowered = str(exc).lower()
    return "unknown column" in lowered or "doesn't exist" in lowered


def _normalize_sort_date_for_signature(value):
    normalized = _coerce_datetime(value)
    if normalized is None:
        return None
    return normalized.strftime("%Y-%m-%d %H:%M:%S")


def _build_search_result_content_signature(
    *,
    title,
    price,
    sort_date,
    url,
    refresh_key,
    seller_store_seq,
    seller_store_name,
    seller_profile_image_url,
    seller_store_level,
    seller_trust_score,
    seller_review_count,
    raw_json,
):
    payload = {
        "title": _safe_text(title),
        "price": _safe_int(price),
        "sort_date": _normalize_sort_date_for_signature(sort_date),
        "url": _safe_text(url) or "",
        "refresh_key": _safe_text(refresh_key),
        "seller_store_seq": _safe_int(seller_store_seq),
        "seller_store_name": _safe_text(seller_store_name),
        "seller_profile_image_url": _safe_text(seller_profile_image_url),
        "seller_store_level": _safe_text(seller_store_level),
        "seller_trust_score": _safe_int(seller_trust_score),
        "seller_review_count": _safe_int(seller_review_count),
        "raw_json_sha256": hashlib.sha256((raw_json or "{}").encode("utf-8")).hexdigest(),
    }
    signature_source = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(signature_source.encode("utf-8")).hexdigest()


def _row_value(row, key, index):
    if isinstance(row, dict):
        return row.get(key)
    if isinstance(row, (tuple, list)):
        if index < len(row):
            return row[index]
    return None


def _fetch_latest_search_result_content_signature(cursor, *, search_query_id, product_id):
    try:
        cursor.execute(
            """
            SELECT
                content_signature,
                title,
                price,
                sort_date,
                url,
                refresh_key,
                seller_store_seq,
                seller_store_name,
                seller_profile_image_url,
                seller_store_level,
                seller_trust_score,
                seller_review_count,
                raw_json
            FROM search_results
            WHERE search_query_id = %s
              AND product_id = %s
            ORDER BY fetched_at DESC, id DESC
            LIMIT 1
            """,
            (search_query_id, product_id),
        )
        row = cursor.fetchone()
        if row is not None:
            existing_signature = _safe_text(_row_value(row, "content_signature", 0))
            if existing_signature:
                return existing_signature
            return _build_search_result_content_signature(
                title=_row_value(row, "title", 1),
                price=_row_value(row, "price", 2),
                sort_date=_row_value(row, "sort_date", 3),
                url=_row_value(row, "url", 4),
                refresh_key=_row_value(row, "refresh_key", 5),
                seller_store_seq=_row_value(row, "seller_store_seq", 6),
                seller_store_name=_row_value(row, "seller_store_name", 7),
                seller_profile_image_url=_row_value(row, "seller_profile_image_url", 8),
                seller_store_level=_row_value(row, "seller_store_level", 9),
                seller_trust_score=_row_value(row, "seller_trust_score", 10),
                seller_review_count=_row_value(row, "seller_review_count", 11),
                raw_json=_safe_text(_row_value(row, "raw_json", 12)) or "{}",
            )
        return None
    except Exception as exc:
        if not _is_unknown_column_error(exc):
            raise

    try:
        cursor.execute(
            """
            SELECT
                title,
                price,
                sort_date,
                url,
                seller_store_seq,
                seller_store_name,
                seller_profile_image_url,
                seller_store_level,
                seller_trust_score,
                seller_review_count,
                raw_json
            FROM search_results
            WHERE search_query_id = %s
              AND product_id = %s
            ORDER BY fetched_at DESC, id DESC
            LIMIT 1
            """,
            (search_query_id, product_id),
        )
        row = cursor.fetchone()
        if row is not None:
            return _build_search_result_content_signature(
                title=_row_value(row, "title", 0),
                price=_row_value(row, "price", 1),
                sort_date=_row_value(row, "sort_date", 2),
                url=_row_value(row, "url", 3),
                refresh_key=None,
                seller_store_seq=_row_value(row, "seller_store_seq", 4),
                seller_store_name=_row_value(row, "seller_store_name", 5),
                seller_profile_image_url=_row_value(row, "seller_profile_image_url", 6),
                seller_store_level=_row_value(row, "seller_store_level", 7),
                seller_trust_score=_row_value(row, "seller_trust_score", 8),
                seller_review_count=_row_value(row, "seller_review_count", 9),
                raw_json=_safe_text(_row_value(row, "raw_json", 10)) or "{}",
            )
        return None
    except Exception as exc:
        if not _is_unknown_column_error(exc):
            raise

    cursor.execute(
        """
        SELECT
            title,
            price,
            sort_date,
            url,
            raw_json
        FROM search_results
        WHERE search_query_id = %s
          AND product_id = %s
        ORDER BY fetched_at DESC, id DESC
        LIMIT 1
        """,
        (search_query_id, product_id),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return _build_search_result_content_signature(
        title=_row_value(row, "title", 0),
        price=_row_value(row, "price", 1),
        sort_date=_row_value(row, "sort_date", 2),
        url=_row_value(row, "url", 3),
        refresh_key=None,
        seller_store_seq=None,
        seller_store_name=None,
        seller_profile_image_url=None,
        seller_store_level=None,
        seller_trust_score=None,
        seller_review_count=None,
        raw_json=_safe_text(_row_value(row, "raw_json", 4)) or "{}",
    )


def _insert_search_result_row(
    cursor,
    *,
    search_query_id,
    product_id,
    title,
    price,
    sort_date,
    url,
    refresh_key,
    seller_store_seq,
    seller_store_name,
    seller_profile_image_url,
    seller_store_level,
    seller_trust_score,
    seller_review_count,
    raw_json,
    content_signature,
    fetched_at,
):
    try:
        cursor.execute(
            """
            INSERT INTO search_results (
                search_query_id,
                product_id,
                title,
                price,
                sort_date,
                url,
                refresh_key,
                seller_store_seq,
                seller_store_name,
                seller_profile_image_url,
                seller_store_level,
                seller_trust_score,
                seller_review_count,
                raw_json,
                content_signature,
                fetched_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                fetched_at = GREATEST(fetched_at, VALUES(fetched_at)),
                title = VALUES(title),
                price = VALUES(price),
                sort_date = VALUES(sort_date),
                url = VALUES(url),
                refresh_key = VALUES(refresh_key),
                seller_store_seq = VALUES(seller_store_seq),
                seller_store_name = VALUES(seller_store_name),
                seller_profile_image_url = VALUES(seller_profile_image_url),
                seller_store_level = VALUES(seller_store_level),
                seller_trust_score = VALUES(seller_trust_score),
                seller_review_count = VALUES(seller_review_count),
                raw_json = VALUES(raw_json)
            """,
            (
                search_query_id,
                product_id,
                title,
                price,
                sort_date,
                url,
                refresh_key,
                seller_store_seq,
                seller_store_name,
                seller_profile_image_url,
                seller_store_level,
                seller_trust_score,
                seller_review_count,
                raw_json,
                content_signature,
                fetched_at,
            ),
        )
        return int(cursor.rowcount or 0)
    except Exception as exc:
        if not _is_unknown_column_error(exc):
            raise

    try:
        cursor.execute(
            """
            INSERT INTO search_results (
                search_query_id,
                product_id,
                title,
                price,
                sort_date,
                url,
                seller_store_seq,
                seller_store_name,
                seller_profile_image_url,
                seller_store_level,
                seller_trust_score,
                seller_review_count,
                raw_json,
                fetched_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                search_query_id,
                product_id,
                title,
                price,
                sort_date,
                url,
                seller_store_seq,
                seller_store_name,
                seller_profile_image_url,
                seller_store_level,
                seller_trust_score,
                seller_review_count,
                raw_json,
                fetched_at,
            ),
        )
        return int(cursor.rowcount or 0)
    except Exception as exc:
        if not _is_unknown_column_error(exc):
            raise

    cursor.execute(
        """
        INSERT INTO search_results (
            search_query_id,
            product_id,
            title,
            price,
            sort_date,
            url,
            raw_json,
            fetched_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            search_query_id,
            product_id,
            title,
            price,
            sort_date,
            url,
            raw_json,
            fetched_at,
        ),
    )
    return int(cursor.rowcount or 0)


def _extract_single_value_row(row):
    if row is None:
        return None
    if isinstance(row, dict):
        if not row:
            return None
        return list(row.values())[0]
    if isinstance(row, (tuple, list)):
        if not row:
            return None
        return row[0]
    return row


def _normalize_setting_id(value):
    normalized = _safe_int(value)
    if normalized is None or normalized <= 0:
        return None
    return normalized


def _target_setting_id(target):
    if not isinstance(target, dict):
        return None
    return _normalize_setting_id(target.get("setting_id") or target.get("rule_id"))


def _has_analysis_job_for_target(cursor, target, product_id, sort_date=None):
    if cursor is None or not isinstance(target, dict):
        return False

    user_id = _normalize_optional_user_id(target.get("user_id"))
    setting_id = _target_setting_id(target)
    normalized_product_id = _safe_text(product_id)
    normalized_sort_date = _coerce_datetime(sort_date)
    if user_id is None or setting_id is None or normalized_product_id is None:
        return False

    try:
        if normalized_sort_date is not None:
            cursor.execute(
                """
                SELECT id
                FROM analysis_jobs
                WHERE user_id = %s
                  AND product_id = %s
                  AND watch_rule_id = %s
                  AND sort_date = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id, normalized_product_id, setting_id, normalized_sort_date),
            )
        else:
            cursor.execute(
                """
                SELECT id
                FROM analysis_jobs
                WHERE user_id = %s
                  AND product_id = %s
                  AND watch_rule_id = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id, normalized_product_id, setting_id),
            )
        row = cursor.fetchone()
        if row is not None:
            return True
    except Exception as exc:
        lowered = str(exc).lower()
        if "unknown column" not in lowered or "sort_date" not in lowered:
            return False
        try:
            cursor.execute(
                """
                SELECT id
                FROM analysis_jobs
                WHERE user_id = %s
                  AND product_id = %s
                  AND watch_rule_id = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id, normalized_product_id, setting_id),
            )
            row = cursor.fetchone()
            return row is not None
        except Exception as nested_exc:
            lowered_nested = str(nested_exc).lower()
            if "unknown column" not in lowered_nested:
                return False
            try:
                cursor.execute(
                    """
                    SELECT id
                    FROM analysis_jobs
                    WHERE user_id = %s
                      AND product_id = %s
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (user_id, normalized_product_id),
                )
                row = cursor.fetchone()
                return row is not None
            except Exception:
                return False

    return False


def _filter_unchanged_targets_needing_backfill(cursor, observed_product, eligible_targets):
    product_id = _safe_text(
        (observed_product or {}).get("product_id")
        or (observed_product or {}).get("seq")
    )
    if product_id is None:
        return []
    normalized_sort_date = _coerce_datetime((observed_product or {}).get("sort_date"))

    backfill_targets = []
    for target in eligible_targets or []:
        if _has_analysis_job_for_target(
            cursor,
            target,
            product_id,
            sort_date=normalized_sort_date,
        ):
            continue
        backfill_targets.append(target)
    return backfill_targets


def _is_schema_missing_error(exc):
    lowered = str(exc).lower()
    return "unknown table" in lowered or _is_unknown_column_error(exc)


def _fetch_store_profile_cache_row(cursor, store_seq):
    if cursor is None:
        return None

    try:
        cursor.execute(
            """
            SELECT
                store_seq,
                store_name,
                fetch_status,
                error_message,
                last_fetched_at,
                next_retry_at
            FROM joongna_store_profiles
            WHERE store_seq = %s
            LIMIT 1
            """,
            (store_seq,),
        )
        row = cursor.fetchone()
    except Exception as exc:
        if _is_schema_missing_error(exc):
            return None
        raise

    if row is None:
        return None

    if isinstance(row, dict):
        return {
            "store_seq": _safe_int(row.get("store_seq")),
            "store_name": _safe_text(row.get("store_name")),
            "fetch_status": _safe_text(row.get("fetch_status")),
            "error_message": _safe_text(row.get("error_message")),
            "last_fetched_at": _coerce_datetime(row.get("last_fetched_at")),
            "next_retry_at": _coerce_datetime(row.get("next_retry_at")),
        }

    if isinstance(row, (tuple, list)):
        return {
            "store_seq": _safe_int(row[0]) if len(row) > 0 else None,
            "store_name": _safe_text(row[1]) if len(row) > 1 else None,
            "fetch_status": _safe_text(row[2]) if len(row) > 2 else None,
            "error_message": _safe_text(row[3]) if len(row) > 3 else None,
            "last_fetched_at": _coerce_datetime(row[4]) if len(row) > 4 else None,
            "next_retry_at": _coerce_datetime(row[5]) if len(row) > 5 else None,
        }

    return None


def _upsert_store_profile_cache_success(cursor, *, store_seq, store_name):
    if cursor is None:
        return
    try:
        cursor.execute(
            """
            INSERT INTO joongna_store_profiles (
                store_seq,
                store_name,
                fetch_status,
                error_message,
                last_fetched_at,
                next_retry_at
            )
            VALUES (%s, %s, 'success', NULL, CURRENT_TIMESTAMP, NULL)
            ON DUPLICATE KEY UPDATE
                store_name = VALUES(store_name),
                fetch_status = 'success',
                error_message = NULL,
                last_fetched_at = CURRENT_TIMESTAMP,
                next_retry_at = NULL
            """,
            (store_seq, store_name),
        )
    except Exception as exc:
        if _is_schema_missing_error(exc):
            return
        raise


def _upsert_store_profile_cache_failure(cursor, *, store_seq, error_message):
    if cursor is None:
        return
    retry_at = datetime.now() + timedelta(minutes=STORE_PROFILE_RETRY_MINUTES)
    try:
        cursor.execute(
            """
            INSERT INTO joongna_store_profiles (
                store_seq,
                store_name,
                fetch_status,
                error_message,
                last_fetched_at,
                next_retry_at
            )
            VALUES (%s, NULL, 'failed', %s, CURRENT_TIMESTAMP, %s)
            ON DUPLICATE KEY UPDATE
                fetch_status = 'failed',
                error_message = VALUES(error_message),
                last_fetched_at = CURRENT_TIMESTAMP,
                next_retry_at = VALUES(next_retry_at)
            """,
            (store_seq, _safe_text(error_message), retry_at),
        )
    except Exception as exc:
        if _is_schema_missing_error(exc):
            return
        raise


def resolve_store_profile_for_store_seq(cursor, store_seq, *, store_profile_cache=None):
    normalized_store_seq = _safe_int(store_seq)
    if normalized_store_seq is None or normalized_store_seq <= 0:
        return None

    if isinstance(store_profile_cache, dict) and normalized_store_seq in store_profile_cache:
        return store_profile_cache.get(normalized_store_seq)

    cached_row = _fetch_store_profile_cache_row(cursor, normalized_store_seq)
    now_dt = datetime.now()
    stale_store_name = None
    if isinstance(cached_row, dict):
        stale_store_name = _safe_text(cached_row.get("store_name"))
        last_fetched_at = _coerce_datetime(cached_row.get("last_fetched_at"))
        next_retry_at = _coerce_datetime(cached_row.get("next_retry_at"))
        # 성공 캐시는 TTL 내에서만 재사용하고, 만료되면 재조회 시도한다.
        if stale_store_name is not None and last_fetched_at is not None:
            elapsed = now_dt - last_fetched_at
            if elapsed < timedelta(hours=STORE_PROFILE_SUCCESS_TTL_HOURS):
                result = {
                    "store_seq": normalized_store_seq,
                    "store_name": stale_store_name,
                }
                if isinstance(store_profile_cache, dict):
                    store_profile_cache[normalized_store_seq] = result
                return result

        # 최근 실패한 storeSeq는 backoff 윈도우 동안 stale 값(또는 None)을 그대로 반환한다.
        if next_retry_at is not None and next_retry_at > now_dt:
            result = {
                "store_seq": normalized_store_seq,
                "store_name": stale_store_name,
            }
            if isinstance(store_profile_cache, dict):
                store_profile_cache[normalized_store_seq] = result
            return result

    try:
        fetched = fetch_joongna_store_profile(normalized_store_seq, raise_on_error=True)
        fetched_store_name = _safe_text((fetched or {}).get("store_name"))
        _upsert_store_profile_cache_success(
            cursor,
            store_seq=normalized_store_seq,
            store_name=fetched_store_name,
        )
        result = {
            "store_seq": normalized_store_seq,
            "store_name": fetched_store_name,
            "profile_image_url": _safe_text((fetched or {}).get("profile_image_url")),
            "store_level": _safe_text((fetched or {}).get("store_level")),
            "trust_score": _safe_int((fetched or {}).get("trust_score")),
            "review_count": _safe_int((fetched or {}).get("review_count")),
        }
    except Exception as exc:
        warning_message = _safe_text(str(exc)) or "store_profile_fetch_failed"
        print(
            "[polling] warning: seller profile 조회 실패 "
            f"(storeSeq={normalized_store_seq}): {warning_message}"
        )
        _upsert_store_profile_cache_failure(
            cursor,
            store_seq=normalized_store_seq,
            error_message=warning_message,
        )
        result = {
            "store_seq": normalized_store_seq,
            "store_name": stale_store_name,
        }

    if isinstance(store_profile_cache, dict):
        store_profile_cache[normalized_store_seq] = result
    return result


def _upsert_search_query(cursor, *, source, normalized_keyword, polled_at, status):
    cursor.execute(
        """
        INSERT INTO search_queries (
            source,
            normalized_keyword,
            created_at,
            last_polled_at,
            last_status
        )
        VALUES (%s, %s, CURRENT_TIMESTAMP, %s, %s)
        ON DUPLICATE KEY UPDATE
            last_polled_at = VALUES(last_polled_at),
            last_status = VALUES(last_status)
        """,
        (
            source,
            normalized_keyword,
            polled_at,
            status,
        ),
    )
    cursor.execute(
        """
        SELECT id
        FROM search_queries
        WHERE source = %s
          AND normalized_keyword = %s
        LIMIT 1
        """,
        (source, normalized_keyword),
    )
    row = cursor.fetchone()
    return _safe_int(_extract_single_value_row(row))


def save_group_search_results(
    cursor,
    *,
    source,
    search_keyword,
    items,
    fetched_at=None,
    status="ok",
    store_profile_cache=None,
):
    normalized_source = _normalize_source(source)
    normalized_keyword = normalize_search_keyword(search_keyword)
    if cursor is None or not normalized_keyword:
        return {
            "ok": False,
            "reason": "invalid_scope",
            "search_query_id": None,
            "inserted_count": 0,
            "skipped_unchanged_count": 0,
        }

    normalized_fetched_at = _coerce_datetime(fetched_at) or datetime.now()
    search_query_id = _upsert_search_query(
        cursor,
        source=normalized_source,
        normalized_keyword=normalized_keyword,
        polled_at=normalized_fetched_at,
        status=status,
    )
    if search_query_id is None:
        return {
            "ok": False,
            "reason": "search_query_upsert_failed",
            "search_query_id": None,
            "inserted_count": 0,
            "skipped_unchanged_count": 0,
        }

    inserted_count = 0
    skipped_unchanged_count = 0
    latest_signature_by_product = {}
    for item in items or []:
        if not isinstance(item, dict):
            continue

        product_id = _safe_text(item.get("product_id") or item.get("seq"))
        if product_id is None:
            continue

        seller_store_seq = _safe_int(
            item.get("seller_store_seq") or item.get("store_seq") or item.get("storeSeq")
        )
        seller_store_name = _safe_text(item.get("seller_store_name"))
        seller_profile_image_url = _safe_text(item.get("seller_profile_image_url"))
        seller_store_level = _safe_text(item.get("seller_store_level"))
        seller_trust_score = _safe_int(item.get("seller_trust_score"))
        seller_review_count = _safe_int(item.get("seller_review_count"))

        if seller_store_seq is not None:
            # search API에는 판매자 닉네임이 없어서 storeSeq 기준 캐시 조회 후 필요 시 상세 API를 호출한다.
            store_profile = resolve_store_profile_for_store_seq(
                cursor,
                seller_store_seq,
                store_profile_cache=store_profile_cache,
            )
            if isinstance(store_profile, dict):
                seller_store_name = _safe_text(store_profile.get("store_name")) or seller_store_name
                seller_profile_image_url = (
                    _safe_text(store_profile.get("profile_image_url")) or seller_profile_image_url
                )
                seller_store_level = _safe_text(store_profile.get("store_level")) or seller_store_level
                seller_trust_score = _safe_int(store_profile.get("trust_score"))
                seller_review_count = _safe_int(store_profile.get("review_count"))

        item["seller_store_seq"] = seller_store_seq
        item["seller_store_name"] = seller_store_name
        item["seller_profile_image_url"] = seller_profile_image_url
        item["seller_store_level"] = seller_store_level
        item["seller_trust_score"] = seller_trust_score
        item["seller_review_count"] = seller_review_count

        title = _safe_text(item.get("title"))
        price = _safe_int(item.get("price"))
        sort_date = _coerce_datetime(item.get("sort_date"))
        url = _safe_text(item.get("product_url")) or ""
        refresh_key = _safe_text(item.get("refresh_key"))
        raw_json = _safe_json_dumps(item)
        content_signature = _build_search_result_content_signature(
            title=title,
            price=price,
            sort_date=sort_date,
            url=url,
            refresh_key=refresh_key,
            seller_store_seq=seller_store_seq,
            seller_store_name=seller_store_name,
            seller_profile_image_url=seller_profile_image_url,
            seller_store_level=seller_store_level,
            seller_trust_score=seller_trust_score,
            seller_review_count=seller_review_count,
            raw_json=raw_json,
        )

        previous_signature = latest_signature_by_product.get(product_id)
        if previous_signature is None:
            previous_signature = _fetch_latest_search_result_content_signature(
                cursor,
                search_query_id=search_query_id,
                product_id=product_id,
            )
            latest_signature_by_product[product_id] = previous_signature

        if previous_signature is not None and previous_signature == content_signature:
            skipped_unchanged_count += 1
            continue

        row_count = _insert_search_result_row(
            cursor,
            search_query_id=search_query_id,
            product_id=product_id,
            title=title,
            price=price,
            sort_date=sort_date,
            url=url,
            refresh_key=refresh_key,
            seller_store_seq=seller_store_seq,
            seller_store_name=seller_store_name,
            seller_profile_image_url=seller_profile_image_url,
            seller_store_level=seller_store_level,
            seller_trust_score=seller_trust_score,
            seller_review_count=seller_review_count,
            raw_json=raw_json,
            content_signature=content_signature,
            fetched_at=normalized_fetched_at,
        )

        if row_count == 1:
            inserted_count += 1
        latest_signature_by_product[product_id] = content_signature

    return {
        "ok": True,
        "reason": "saved",
        "search_query_id": search_query_id,
        "inserted_count": inserted_count,
        "skipped_unchanged_count": skipped_unchanged_count,
    }


def _build_source_search_group_key(source, search_keyword):
    normalized_source = _normalize_source(source)
    normalized_keyword = normalize_search_keyword(search_keyword)
    if not normalized_keyword:
        return None
    return normalized_source, normalized_keyword.lower()


def group_watch_rules_by_search_source(keyword_targets):
    group_map = {}
    group_order = []

    for search_keyword, targets in (keyword_targets or {}).items():
        for target in targets or []:
            source = _normalize_source(target.get("source"))
            group_key = _build_source_search_group_key(source, search_keyword)
            if group_key is None:
                continue

            group = group_map.get(group_key)
            if group is None:
                normalized_source = group_key[0]
                normalized_keyword = normalize_search_keyword(search_keyword)
                group = {
                    "source": normalized_source,
                    "search_keyword": normalized_keyword,
                    "targets": [],
                }
                group_map[group_key] = group
                group_order.append(group_key)

            target_copy = dict(target)
            target_copy["source"] = group["source"]
            target_copy["search_keyword"] = group["search_keyword"]
            group["targets"].append(target_copy)

    groups = []
    for group_key in group_order:
        group = group_map.get(group_key)
        if not group:
            continue
        groups.append(group)
    return groups


def collect_active_watch_rules(user_id=None, search_words=None):
    words, keyword_targets, due_rules, target_source = _resolve_poll_targets(search_words, user_id)
    groups = group_watch_rules_by_search_source(keyword_targets)
    return {
        "words": words,
        "keyword_targets": keyword_targets,
        "due_rules": due_rules,
        "target_source": target_source,
        "groups": groups,
    }


def fetch_once_per_group(group):
    source = _normalize_source((group or {}).get("source"))
    search_keyword = normalize_search_keyword((group or {}).get("search_keyword"))
    if not search_keyword:
        return {
            "ok": False,
            "reason": "invalid_search_keyword",
            "source": source,
            "search_keyword": search_keyword,
            "items": [],
        }

    if source != "joongna":
        return {
            "ok": False,
            "reason": "unsupported_source",
            "source": source,
            "search_keyword": search_keyword,
            "items": [],
        }

    items = search_joongna_products(search_keyword)
    return {
        "ok": True,
        "reason": "ok",
        "source": source,
        "search_keyword": search_keyword,
        "items": items,
    }


def save_polled_listings(observed_products, *, evaluate_and_store):
    saved_results = []
    for observed_product in observed_products:
        product_state = evaluate_and_store(observed_product)
        if product_state is None:
            continue
        saved_results.append(
            {
                "observed_product": observed_product,
                "product_state": product_state,
            }
        )
    return saved_results


def _filter_targets_by_saved_window(observed_product, targets):
    listing_sort_date = _coerce_datetime((observed_product or {}).get("sort_date"))
    if listing_sort_date is None:
        return []

    eligible_targets = []
    for target in targets or []:
        saved_at = _coerce_datetime(target.get("saved_at"))
        if saved_at is None:
            continue
        if listing_sort_date >= saved_at:
            eligible_targets.append(target)
    return eligible_targets


def match_saved_listings_to_watch_rules(saved_listing_states, targets, *, stats):
    matches = []
    for item in saved_listing_states:
        observed_product = item.get("observed_product") or {}
        product_state = item.get("product_state") or {}
        eligible_targets = _filter_targets_by_saved_window(observed_product, targets)
        if not eligible_targets:
            stats["skipped_before_saved_at"] += len(targets or [])
            continue

        stats["matched_watch_rules"] += len(eligible_targets)
        matches.append(
            {
                "observed_product": observed_product,
                "eligible_targets": eligible_targets,
                "change_reason": product_state.get("change_reason"),
            }
        )
    return matches


def create_alerts_for_matches(matches, *, stats):
    for match in matches:
        observed_product = match.get("observed_product") or {}
        eligible_targets = match.get("eligible_targets") or []
        change_reason = match.get("change_reason")

        try:
            enqueue_result = enqueue_analysis_for_product(
                observed_product,
                eligible_targets,
                change_reason,
            )
            created_jobs = enqueue_result.get("created_jobs") or []
            skipped_jobs = enqueue_result.get("skipped_jobs") or []
            stats["analysis_jobs_created"] += len(created_jobs)
            stats["analysis_jobs_skipped_duplicate"] += len(skipped_jobs)
            stats["created_alert_count"] += len(created_jobs)
            stats["alert_created_count"] += len(created_jobs)
        except Exception as exc:
            stats["db_errors"] += 1
            product_id = observed_product.get("product_id")
            search_keyword = observed_product.get("search_keyword")
            print(
                f"[{search_keyword}] analysis job enqueue 실패 "
                f"(seq={product_id}): {exc}"
            )


def upsert_seen_product_and_detect_change(
    cursor,
    observed_product,
    *,
    seen_db_ready,
    on_db_error,
):
    if not seen_db_ready or cursor is None:
        return {
            "should_analyze": True,
            "change_reason": "new",
            "existing": None,
        }

    existing = get_seen_product(cursor, observed_product.get("product_id"))
    change_reason = detect_listing_change(existing, observed_product)
    should_analyze = should_analyze_listing(change_reason)
    status = "analysis_pending" if should_analyze else "unchanged"

    try:
        upsert_seen_product_observation(
            cursor,
            observed_product,
            change_reason=change_reason,
            status=status,
        )
    except Exception as exc:
        on_db_error(exc)
        return {
            "should_analyze": True,
            "change_reason": "new",
            "existing": existing,
        }

    return {
        "should_analyze": should_analyze,
        "change_reason": change_reason,
        "existing": existing,
    }


def select_matches_for_analysis(matches, *, cursor=None, stats=None):
    selected_matches = []
    for match in matches or []:
        change_reason = _safe_text((match or {}).get("change_reason"))
        if should_analyze_listing(change_reason):
            selected_matches.append(match)
            continue

        if change_reason != "unchanged":
            continue

        observed_product = (match or {}).get("observed_product") or {}
        eligible_targets = (match or {}).get("eligible_targets") or []
        backfill_targets = _filter_unchanged_targets_needing_backfill(
            cursor,
            observed_product,
            eligible_targets,
        )
        if not backfill_targets:
            continue

        if isinstance(stats, dict):
            stats["unchanged_backfill_match_count"] = (
                int(stats.get("unchanged_backfill_match_count") or 0) + 1
            )
            stats["unchanged_backfill_target_count"] = (
                int(stats.get("unchanged_backfill_target_count") or 0) + len(backfill_targets)
            )

        selected_matches.append(
            {
                "observed_product": observed_product,
                "eligible_targets": backfill_targets,
                "change_reason": "unchanged_backfill",
            }
        )

    return selected_matches


def _build_keyword_targets_from_user_fair_prices(watch_rules):
    keyword_targets = {}
    target_keys = set()

    for rule in watch_rules:
        if rule.get("enabled") is not None and not bool(rule.get("enabled")):
            continue
        if "last_poll_requested_at" in rule and rule.get("last_poll_requested_at") is None:
            continue

        search_keyword = normalize_search_keyword(rule.get("search_keyword"))
        user_id = _normalize_optional_user_id(rule.get("user_id"))
        if not search_keyword or not user_id:
            continue

        setting_id = rule.get("id")
        target_key = (search_keyword.lower(), user_id, setting_id)
        if target_key in target_keys:
            continue
        target_keys.add(target_key)

        target = {
            "user_id": user_id,
            "rule_id": setting_id,
            "setting_id": setting_id,
            "setting_ids": [setting_id] if setting_id is not None else [],
            "saved_at": rule.get("saved_at"),
            "search_keyword": search_keyword,
            "watch_rule": None,
        }
        keyword_targets.setdefault(search_keyword, []).append(target)

    return keyword_targets


def _build_keyword_targets_from_watch_rules(watch_rules):
    # Deprecated: watch_rule fanout은 사용하지 않고 user_fair_prices 기반 사용자 타겟만 유지
    return _build_keyword_targets_from_user_fair_prices(watch_rules)


def _resolve_poll_targets(search_words, user_id):
    normalized_user_id = _normalize_optional_user_id(user_id)

    try:
        due_rules = get_due_watch_rules(user_id=normalized_user_id)
    except Exception as exc:
        print(f"[polling] user_fair_prices(enabled) 조회 실패, polling 스킵: {exc}")
        return [], {}, [], "settings_error"

    keyword_targets = _build_keyword_targets_from_user_fair_prices(due_rules)

    if search_words:
        requested_words = _normalize_search_words(search_words)
        requested_word_set = set()
        for word in requested_words:
            normalized = normalize_search_keyword(word)
            if normalized:
                requested_word_set.add(normalized.lower())

        filtered_targets = {}
        for keyword, targets in keyword_targets.items():
            if keyword.lower() in requested_word_set:
                filtered_targets[keyword] = targets

        words = list(filtered_targets.keys())
        return words, filtered_targets, due_rules, "cli"

    if keyword_targets:
        words = list(keyword_targets.keys())
        return words, keyword_targets, due_rules, "settings"

    return [], {}, due_rules, "settings_empty"


def poll_once(user_id=None, search_words=None, *, inline_process=False, inline_process_limit=50):
    poll_context = collect_active_watch_rules(user_id=user_id, search_words=search_words)
    words = poll_context.get("words") or []
    due_rules = poll_context.get("due_rules") or []
    target_source = poll_context.get("target_source")
    groups = poll_context.get("groups") or []
    stats = _build_poll_stats(words)
    stats["settings_due"] = len(due_rules)
    stats["polling_group_count"] = len(groups)

    if not groups:
        if target_source == "settings":
            if due_rules:
                print("[polling] due watch_rule은 있으나 유효한 검색어가 없어 이번 주기는 스킵합니다.")
            else:
                print(
                    "[polling] 이번 주기 due 대상 검색어가 없어 스킵합니다. "
                    "(enabled=true라도 polling interval 미도래 시 제외)"
                )
        elif target_source == "cli":
            print("[polling] 요청한 검색어에 매칭되는 due 대상이 없어 이번 주기는 스킵합니다.")
        else:
            print("[polling] polling 대상 검색어가 없어 이번 주기는 스킵합니다.")
        return stats

    connection = None
    cursor = None
    seen_db_ready = False
    search_cache_db_ready = False
    processed_products = {}
    store_profile_cache = {}

    def disable_seen_db(reason):
        nonlocal connection, cursor, seen_db_ready, search_cache_db_ready
        seen_db_ready = False
        search_cache_db_ready = False
        print(f"[polling] seen DB 비활성화: {reason}")
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
            cursor = None
        if connection is not None and connection.is_connected():
            try:
                connection.close()
            except Exception:
                pass
            connection = None

    def mark_related_rules_polled(targets):
        if target_source != "settings":
            return

        marked_rule_ids = set()
        for target in targets:
            setting_ids = target.get("setting_ids")
            if not setting_ids:
                fallback_setting_id = target.get("setting_id") or target.get("rule_id")
                setting_ids = [fallback_setting_id] if fallback_setting_id is not None else []

            for setting_id in setting_ids:
                if setting_id is None or setting_id in marked_rule_ids:
                    continue
                marked_rule_ids.add(setting_id)

                try:
                    mark_watch_rule_polled(setting_id)
                    stats["settings_marked"] += 1
                except Exception as exc:
                    stats["db_errors"] += 1
                    print(f"[polling] setting polled_at 갱신 실패 (setting_id={setting_id}): {exc}")

    try:
        try:
            connection = get_connection()
            cursor = connection.cursor()
            seen_db_ready = True
            search_cache_db_ready = True
        except Exception as exc:
            print(f"[polling] seen DB 연결 실패: {exc}")

        for group in groups:
            source = _normalize_source(group.get("source"))
            search_word = normalize_search_keyword(group.get("search_keyword")) or ""
            targets_for_word = group.get("targets") or []
            search_completed_for_word = False

            try:
                print(f"[{source}/{search_word}] Search API 조회 시작")
                try:
                    stats["external_api_calls"] += 1
                    fetch_result = fetch_once_per_group(group)
                    if not fetch_result.get("ok"):
                        raise RuntimeError(fetch_result.get("reason") or "search_fetch_failed")
                    items = fetch_result.get("items") or []
                    search_completed_for_word = True
                    stats["fetched_items"] += len(items)
                    stats["fetched_count"] += len(items)
                    print(f"[{source}/{search_word}] 검색 결과 {len(items)}건")
                except Exception as exc:
                    stats["search_errors"] += 1
                    print(f"[{source}/{search_word}] Search API 조회 실패: {exc}")
                    if search_cache_db_ready and cursor is not None:
                        try:
                            save_group_search_results(
                                cursor,
                                source=source,
                                search_keyword=search_word,
                                items=[],
                                fetched_at=datetime.now(),
                                status="fetch_error",
                                store_profile_cache=store_profile_cache,
                            )
                            connection.commit()
                        except Exception as cache_exc:
                            stats["search_results_save_errors"] += 1
                            try:
                                connection.rollback()
                            except Exception:
                                pass
                            search_cache_db_ready = False
                            print(
                                f"[{source}/{search_word}] search cache 상태 저장 실패: "
                                f"{cache_exc}"
                            )
                    continue

                if search_cache_db_ready and cursor is not None:
                    try:
                        save_result = save_group_search_results(
                            cursor,
                            source=source,
                            search_keyword=search_word,
                            items=items,
                            fetched_at=datetime.now(),
                            status="ok",
                            store_profile_cache=store_profile_cache,
                        )
                        if save_result.get("ok"):
                            connection.commit()
                            inserted_count = int(save_result.get("inserted_count") or 0)
                            skipped_unchanged_count = int(
                                save_result.get("skipped_unchanged_count") or 0
                            )
                            stats["search_results_saved"] += inserted_count
                            stats["search_results_skipped_unchanged"] += skipped_unchanged_count
                        else:
                            stats["search_results_save_errors"] += 1
                            print(
                                f"[{source}/{search_word}] search cache 저장 실패: "
                                f"{save_result.get('reason') or 'unknown'}"
                            )
                    except Exception as exc:
                        stats["search_results_save_errors"] += 1
                        try:
                            connection.rollback()
                        except Exception:
                            pass
                        search_cache_db_ready = False
                        print(f"[{source}/{search_word}] search cache 저장 예외: {exc}")

                observed_products = []
                for item in items:
                    observed_product = _build_observed_product(search_word, item)
                    observed_products.append(observed_product)

                def evaluate_and_store(observed_product):
                    nonlocal seen_db_ready
                    product_id = observed_product.get("product_id")
                    if product_id is None:
                        stats["skipped_no_seq"] += 1
                        return None

                    product_state = processed_products.get(product_id)
                    if product_state is not None:
                        return product_state

                    def _handle_seen_db_error(exc):
                        nonlocal seen_db_ready
                        stats["db_errors"] += 1
                        try:
                            connection.rollback()
                        except Exception:
                            pass
                        print(f"[{search_word}] seen 관측 처리 실패 (seq={product_id}): {exc}")
                        disable_seen_db(str(exc))

                    if seen_db_ready and cursor is not None:
                        try:
                            detected = upsert_seen_product_and_detect_change(
                                cursor,
                                observed_product,
                                seen_db_ready=seen_db_ready,
                                on_db_error=_handle_seen_db_error,
                            )
                            connection.commit()
                        except Exception as exc:
                            _handle_seen_db_error(exc)
                            detected = {
                                "should_analyze": True,
                                "change_reason": "new",
                            }
                    else:
                        detected = {
                            "should_analyze": True,
                            "change_reason": "new",
                        }

                    should_analyze = bool(detected.get("should_analyze"))
                    change_reason = detected.get("change_reason") or "new"

                    product_state = {
                        "should_analyze": should_analyze,
                        "change_reason": change_reason,
                    }
                    processed_products[product_id] = product_state

                    if change_reason == "new":
                        stats["new_count"] += 1
                    elif change_reason == "unchanged":
                        stats["unchanged_skipped_count"] += 1
                    else:
                        stats["changed_count"] += 1

                    if not should_analyze:
                        stats["skipped_seen"] += 1
                        print(f"[{search_word}] 상태 동일(글로벌) (seq={product_id}, reason={change_reason})")

                    if should_analyze:
                        stats["analyzed_count"] += 1
                        print(
                            f"[{search_word}] 분석 큐 등록 대상 감지 "
                            f"(seq={product_id}, reason={change_reason})"
                        )
                        stats["new_items"] += 1

                    return product_state

                saved_listing_states = save_polled_listings(
                    observed_products,
                    evaluate_and_store=evaluate_and_store,
                )
                matches = match_saved_listings_to_watch_rules(
                    saved_listing_states,
                    targets_for_word,
                    stats=stats,
                )
                selected_matches = select_matches_for_analysis(matches, cursor=cursor, stats=stats)
                create_alerts_for_matches(selected_matches, stats=stats)
            finally:
                if search_completed_for_word:
                    mark_related_rules_polled(targets_for_word)
                elif target_source == "settings" and targets_for_word:
                    print(
                        f"[{source}/{search_word}] Search API 실패로 setting polled_at 갱신 생략 "
                        "(force_poll 유지)"
                    )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

    if inline_process:
        print("[polling] inline_process=True 요청이 들어왔지만 enqueue-only 정책으로 무시합니다.")

    print(
        "[polling] group_summary "
        f"groups={stats.get('polling_group_count', 0)} "
        f"external_calls={stats.get('external_api_calls', 0)} "
        f"matched_watch_rules={stats.get('matched_watch_rules', 0)} "
        f"created_alerts={stats.get('created_alert_count', 0)}"
    )
    print(
        "[polling] change_summary "
        f"fetched_count={stats.get('fetched_count', 0)} "
        f"new_count={stats.get('new_count', 0)} "
        f"changed_count={stats.get('changed_count', 0)} "
        f"unchanged_skipped_count={stats.get('unchanged_skipped_count', 0)} "
        f"unchanged_backfill_match_count={stats.get('unchanged_backfill_match_count', 0)} "
        f"unchanged_backfill_target_count={stats.get('unchanged_backfill_target_count', 0)} "
        f"analyzed_count={stats.get('analyzed_count', 0)} "
        f"alert_created_count={stats.get('alert_created_count', 0)}"
    )
    print(
        "[polling] search_cache_summary "
        f"search_results_saved={stats.get('search_results_saved', 0)} "
        f"search_results_skipped_unchanged={stats.get('search_results_skipped_unchanged', 0)} "
        f"search_results_save_errors={stats.get('search_results_save_errors', 0)}"
    )

    return stats
