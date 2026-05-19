import re
import hashlib
import json
from datetime import datetime, timezone


UNKNOWN_COLUMN_ERRNO = 1054
CHANGE_REASON_NEW = "new"
CHANGE_REASON_SORT_DATE_CHANGED = "sort_date_changed"
CHANGE_REASON_PRICE_CHANGED = "price_changed"
CHANGE_REASON_TITLE_CHANGED = "title_changed"
CHANGE_REASON_BODY_MAYBE_CHANGED = "body_maybe_changed"
CHANGE_REASON_REFRESH_KEY_CHANGED = "refresh_key_changed"
CHANGE_REASON_UNCHANGED = "unchanged"

ANALYZE_REQUIRED_CHANGE_REASONS = {
    CHANGE_REASON_NEW,
    CHANGE_REASON_SORT_DATE_CHANGED,
    CHANGE_REASON_PRICE_CHANGED,
    CHANGE_REASON_TITLE_CHANGED,
    CHANGE_REASON_BODY_MAYBE_CHANGED,
    CHANGE_REASON_REFRESH_KEY_CHANGED,
}
WRITE_REQUIRED_CHANGE_REASONS = set(ANALYZE_REQUIRED_CHANGE_REASONS)


def _coerce_product_id(product_id):
    if product_id is None or isinstance(product_id, bool):
        return None

    if isinstance(product_id, int):
        return product_id if product_id > 0 else None

    if isinstance(product_id, float):
        normalized = int(product_id)
        return normalized if normalized > 0 else None

    if isinstance(product_id, str):
        digits = re.sub(r"[^0-9]", "", product_id)
        if not digits:
            return None
        normalized = int(digits)
        return normalized if normalized > 0 else None

    return None


def _coerce_price(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        digits = re.sub(r"[^0-9-]", "", value)
        if not digits:
            return None
        try:
            return int(digits)
        except ValueError:
            return None
    return None


def _coerce_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None

    cleaned = str(value).strip()
    return cleaned or None


def normalize_title_for_compare(title):
    normalized_title = _coerce_text(title)
    if normalized_title is None:
        return None

    normalized_title = normalized_title.lower()
    normalized_title = re.sub(r"\s+", "", normalized_title)
    return normalized_title or None


def normalize_price_for_compare(price):
    return _coerce_price(price)


def _coerce_sort_date_datetime(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        parsed = value
    else:
        text = _coerce_text(value)
        if text is None:
            return None

        normalized_text = text.replace("Z", "+00:00")
        parsed = None
        try:
            parsed = datetime.fromisoformat(normalized_text)
        except ValueError:
            pass

        if parsed is None:
            for date_format in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y/%m/%d %H:%M:%S",
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


def _build_stable_hash(value):
    if value is None:
        return None

    if isinstance(value, str):
        payload = value.strip()
    else:
        try:
            payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        except Exception:
            payload = str(value).strip()

    if not payload:
        return None

    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _resolve_body_fingerprint(record):
    if not isinstance(record, dict):
        return None

    for key in ("body_hash", "content_hash", "self_check_hash", "body_fingerprint", "content_fingerprint"):
        hashed_value = _coerce_text(record.get(key))
        if hashed_value:
            return hashed_value

    if record.get("self_check_fields") is not None:
        hashed_self_check = _build_stable_hash(record.get("self_check_fields"))
        if hashed_self_check:
            return hashed_self_check

    for key in ("body_text", "body", "content", "description"):
        raw_text = _coerce_text(record.get(key))
        if raw_text:
            hashed_text = _build_stable_hash(raw_text)
            if hashed_text:
                return hashed_text

    return None


def _is_unknown_column_error(exc):
    if getattr(exc, "errno", None) == UNKNOWN_COLUMN_ERRNO:
        return True
    return "Unknown column" in str(exc)


def get_seen_product(cursor, product_id):
    normalized_id = _coerce_product_id(product_id)
    if normalized_id is None:
        return None

    try:
        cursor.execute(
            """
            SELECT
                seq,
                product_url,
                title,
                price,
                last_title,
                last_price_krw,
                last_refresh_key,
                last_sort_date,
                previous_sort_date,
                sort_date_changed_count,
                last_sort_date_changed_at,
                last_change_reason,
                last_seen_at,
                last_analyzed_at,
                seen_count
            FROM joongna_seen_products
            WHERE seq = %s
            LIMIT 1
            """,
            (normalized_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        return {
            "seq": _coerce_product_id(row[0]),
            "product_url": _coerce_text(row[1]),
            "title": _coerce_text(row[2]),
            "price": _coerce_price(row[3]),
            "last_title": _coerce_text(row[4]),
            "last_price_krw": _coerce_price(row[5]),
            "last_refresh_key": _coerce_text(row[6]),
            "last_sort_date": _coerce_sort_date_datetime(row[7]),
            "previous_sort_date": _coerce_sort_date_datetime(row[8]),
            "sort_date_changed_count": int(row[9]) if row[9] is not None else 0,
            "last_sort_date_changed_at": row[10],
            "last_change_reason": _coerce_text(row[11]),
            "last_seen_at": row[12],
            "last_analyzed_at": row[13],
            "seen_count": row[14],
        }
    except Exception as exc:
        if not _is_unknown_column_error(exc):
            raise

    cursor.execute(
        """
        SELECT
            seq,
            product_url,
            title,
            price,
            first_seen_at
        FROM joongna_seen_products
        WHERE seq = %s
        LIMIT 1
        """,
        (normalized_id,),
    )
    legacy_row = cursor.fetchone()
    if legacy_row is None:
        return None

    return {
        "seq": _coerce_product_id(legacy_row[0]),
        "product_url": _coerce_text(legacy_row[1]),
        "title": _coerce_text(legacy_row[2]),
        "price": _coerce_price(legacy_row[3]),
        "last_title": _coerce_text(legacy_row[2]),
        "last_price_krw": _coerce_price(legacy_row[3]),
        "last_refresh_key": None,
        "last_sort_date": None,
        "previous_sort_date": None,
        "sort_date_changed_count": 0,
        "last_sort_date_changed_at": None,
        "last_change_reason": None,
        "last_seen_at": legacy_row[4],
        "last_analyzed_at": None,
        "seen_count": 1,
    }


def detect_listing_change(previous, current):
    if not previous:
        return CHANGE_REASON_NEW

    previous_title = normalize_title_for_compare(previous.get("last_title"))
    if previous_title is None:
        previous_title = normalize_title_for_compare(previous.get("title"))
    current_title = normalize_title_for_compare(current.get("title"))
    if previous_title != current_title:
        return CHANGE_REASON_TITLE_CHANGED

    previous_price = normalize_price_for_compare(previous.get("last_price_krw"))
    if previous_price is None:
        previous_price = normalize_price_for_compare(previous.get("price"))
    current_price = normalize_price_for_compare(current.get("price"))
    if previous_price != current_price:
        return CHANGE_REASON_PRICE_CHANGED

    previous_sort_date = _coerce_sort_date_datetime(previous.get("last_sort_date"))
    current_sort_date = _coerce_sort_date_datetime(current.get("sort_date"))
    if previous_sort_date is not None and current_sort_date is not None and previous_sort_date != current_sort_date:
        return CHANGE_REASON_SORT_DATE_CHANGED

    previous_refresh_key = _coerce_text(previous.get("last_refresh_key"))
    current_refresh_key = _coerce_text(current.get("refresh_key"))
    if previous_refresh_key != current_refresh_key:
        return CHANGE_REASON_REFRESH_KEY_CHANGED

    previous_body_fingerprint = _resolve_body_fingerprint(previous)
    current_body_fingerprint = _resolve_body_fingerprint(current)
    if previous_body_fingerprint and current_body_fingerprint and previous_body_fingerprint != current_body_fingerprint:
        return CHANGE_REASON_BODY_MAYBE_CHANGED

    return CHANGE_REASON_UNCHANGED


def should_analyze_listing(change_reason):
    normalized_reason = _coerce_text(change_reason)
    if normalized_reason == "new_product":
        normalized_reason = CHANGE_REASON_NEW
    return normalized_reason in ANALYZE_REQUIRED_CHANGE_REASONS


def should_write_seen_product(change_reason):
    normalized_reason = _coerce_text(change_reason)
    if normalized_reason == "new_product":
        normalized_reason = CHANGE_REASON_NEW
    return normalized_reason in WRITE_REQUIRED_CHANGE_REASONS


def should_analyze_seen_product(existing, current):
    change_reason = detect_listing_change(existing, current)
    return should_analyze_listing(change_reason), change_reason


def upsert_seen_product_observation(
    cursor,
    product,
    *,
    change_reason=None,
    status=None,
):
    product_id = _coerce_product_id(product.get("product_id") or product.get("seq"))
    if product_id is None:
        raise ValueError("product_id/seq가 없습니다.")

    title = _coerce_text(product.get("title"))
    price_krw = _coerce_price(product.get("price"))
    refresh_key = _coerce_text(product.get("refresh_key"))
    search_word = _coerce_text(product.get("search_word")) or ""
    product_url = _coerce_text(product.get("product_url")) or ""
    image_url = _coerce_text(product.get("image_url"))
    sort_date = _coerce_text(product.get("sort_date"))
    sort_date_datetime = _coerce_sort_date_datetime(sort_date)
    normalized_status = _coerce_text(status)
    normalized_reason = _coerce_text(change_reason)

    try:
        cursor.execute(
            """
            INSERT INTO joongna_seen_products (
                seq,
                search_word,
                title,
                price,
                product_url,
                image_url,
                sort_date,
                first_seen_at,
                last_seen_at,
                seen_count,
                last_title,
                last_price_krw,
                last_status,
                last_refresh_key,
                last_sort_date,
                previous_sort_date,
                sort_date_changed_count,
                last_sort_date_changed_at,
                last_change_reason
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1,
                %s, %s, %s, %s, %s, NULL, 0, NULL, %s
            )
            ON DUPLICATE KEY UPDATE
                search_word = VALUES(search_word),
                title = VALUES(title),
                price = VALUES(price),
                product_url = VALUES(product_url),
                image_url = VALUES(image_url),
                sort_date = VALUES(sort_date),
                last_seen_at = CURRENT_TIMESTAMP,
                seen_count = COALESCE(seen_count, 0) + 1,
                last_title = VALUES(last_title),
                last_price_krw = VALUES(last_price_krw),
                last_status = VALUES(last_status),
                last_refresh_key = VALUES(last_refresh_key),
                last_sort_date = CASE
                    WHEN VALUES(last_sort_date) IS NOT NULL
                         AND COALESCE(VALUES(last_change_reason), '') = 'sort_date_changed'
                        THEN VALUES(last_sort_date)
                    WHEN last_sort_date IS NULL AND VALUES(last_sort_date) IS NOT NULL
                        THEN VALUES(last_sort_date)
                    ELSE last_sort_date
                END,
                previous_sort_date = CASE
                    WHEN VALUES(last_sort_date) IS NOT NULL
                         AND COALESCE(VALUES(last_change_reason), '') = 'sort_date_changed'
                        THEN last_sort_date
                    ELSE previous_sort_date
                END,
                sort_date_changed_count = CASE
                    WHEN VALUES(last_sort_date) IS NOT NULL
                         AND COALESCE(VALUES(last_change_reason), '') = 'sort_date_changed'
                        THEN COALESCE(sort_date_changed_count, 0) + 1
                    ELSE COALESCE(sort_date_changed_count, 0)
                END,
                last_sort_date_changed_at = CASE
                    WHEN VALUES(last_sort_date) IS NOT NULL
                         AND COALESCE(VALUES(last_change_reason), '') = 'sort_date_changed'
                        THEN CURRENT_TIMESTAMP
                    ELSE last_sort_date_changed_at
                END,
                last_change_reason = VALUES(last_change_reason)
            """,
            (
                product_id,
                search_word,
                title,
                price_krw,
                product_url,
                image_url,
                sort_date,
                title,
                price_krw,
                normalized_status,
                refresh_key,
                sort_date_datetime,
                normalized_reason,
            ),
        )
        return
    except Exception as exc:
        if not _is_unknown_column_error(exc):
            raise

    cursor.execute(
        """
        INSERT INTO joongna_seen_products (
            seq,
            search_word,
            title,
            price,
            product_url,
            image_url,
            sort_date
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            search_word = VALUES(search_word),
            title = VALUES(title),
            price = VALUES(price),
            product_url = VALUES(product_url),
            image_url = VALUES(image_url),
            sort_date = VALUES(sort_date)
        """,
        (
            product_id,
            search_word,
            title,
            price_krw,
            product_url,
            image_url,
            sort_date,
        ),
    )


def mark_seen_product_analyzed(cursor, product_id, *, status="analyzed"):
    normalized_id = _coerce_product_id(product_id)
    if normalized_id is None:
        raise ValueError("product_id/seq가 없습니다.")

    normalized_status = _coerce_text(status) or "analyzed"

    try:
        cursor.execute(
            """
            UPDATE joongna_seen_products
            SET
                last_analyzed_at = CURRENT_TIMESTAMP,
                last_status = %s
            WHERE seq = %s
            """,
            (normalized_status, normalized_id),
        )
        return
    except Exception as exc:
        if not _is_unknown_column_error(exc):
            raise
