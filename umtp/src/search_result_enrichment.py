import hashlib
import json


UNKNOWN_COLUMN_ERRNO = 1054


def _is_missing_schema_error(exc):
    if getattr(exc, "errno", None) == UNKNOWN_COLUMN_ERRNO:
        return True
    lowered = str(exc).lower()
    return "unknown column" in lowered or "doesn't exist" in lowered


def _text(value):
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _row_value(row, key, index):
    if isinstance(row, dict):
        return row.get(key)
    if isinstance(row, (tuple, list)) and index < len(row):
        return row[index]
    return None


def build_body_hash(body_text):
    normalized = _text(body_text)
    if normalized is None:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def load_latest_search_result(cursor, product_id):
    if cursor is None or product_id is None:
        return None
    try:
        cursor.execute(
            """
            SELECT
                id, product_id, title, price, sort_date, url, body_text,
                body_hash, body_fetched_at, self_check_json,
                seller_store_seq, seller_store_name,
                seller_profile_image_url, seller_store_level,
                seller_trust_score, seller_review_count
            FROM search_results
            WHERE product_id = %s
            ORDER BY fetched_at DESC, id DESC
            LIMIT 1
            """,
            (str(product_id),),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return {
            "id": _row_value(row, "id", 0),
            "product_id": _row_value(row, "product_id", 1),
            "title": _row_value(row, "title", 2),
            "price": _row_value(row, "price", 3),
            "sort_date": _row_value(row, "sort_date", 4),
            "url": _row_value(row, "url", 5),
            "body_text": _row_value(row, "body_text", 6),
            "body_hash": _row_value(row, "body_hash", 7),
            "body_fetched_at": _row_value(row, "body_fetched_at", 8),
            "self_check_json": _row_value(row, "self_check_json", 9),
            "seller_store_seq": _row_value(row, "seller_store_seq", 10),
            "seller_store_name": _row_value(row, "seller_store_name", 11),
            "seller_profile_image_url": _row_value(row, "seller_profile_image_url", 12),
            "seller_store_level": _row_value(row, "seller_store_level", 13),
            "seller_trust_score": _row_value(row, "seller_trust_score", 14),
            "seller_review_count": _row_value(row, "seller_review_count", 15),
        }
    except Exception as exc:
        if not _is_missing_schema_error(exc):
            raise

    try:
        cursor.execute(
            """
            SELECT
                id, product_id, title, price, sort_date, url, body_text,
                seller_store_seq, seller_store_name,
                seller_profile_image_url, seller_store_level,
                seller_trust_score, seller_review_count
            FROM search_results
            WHERE product_id = %s
            ORDER BY fetched_at DESC, id DESC
            LIMIT 1
            """,
            (str(product_id),),
        )
        row = cursor.fetchone()
    except Exception as exc:
        if _is_missing_schema_error(exc):
            return None
        raise
    if row is None:
        return None
    body_text = _row_value(row, "body_text", 6)
    return {
        "id": _row_value(row, "id", 0),
        "product_id": _row_value(row, "product_id", 1),
        "title": _row_value(row, "title", 2),
        "price": _row_value(row, "price", 3),
        "sort_date": _row_value(row, "sort_date", 4),
        "url": _row_value(row, "url", 5),
        "body_text": body_text,
        "body_hash": build_body_hash(body_text),
        "body_fetched_at": None,
        "self_check_json": None,
        "seller_store_seq": _row_value(row, "seller_store_seq", 7),
        "seller_store_name": _row_value(row, "seller_store_name", 8),
        "seller_profile_image_url": _row_value(row, "seller_profile_image_url", 9),
        "seller_store_level": _row_value(row, "seller_store_level", 10),
        "seller_trust_score": _row_value(row, "seller_trust_score", 11),
        "seller_review_count": _row_value(row, "seller_review_count", 12),
    }


def persist_latest_search_result_enrichment(
    cursor,
    product_id,
    *,
    body_text=None,
    self_check_fields=None,
    seller_profile=None,
):
    if cursor is None or product_id is None:
        return {"updated": False, "reason": "invalid_scope"}
    normalized_body = _text(body_text)
    body_hash = build_body_hash(normalized_body)
    self_check_json = None
    if isinstance(self_check_fields, dict):
        self_check_json = json.dumps(
            self_check_fields,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    profile = seller_profile if isinstance(seller_profile, dict) else {}
    values = (
        str(product_id),
        normalized_body,
        body_hash,
        self_check_json,
        profile.get("store_seq"),
        _text(profile.get("store_name")),
        _text(profile.get("profile_image_url")),
        _text(profile.get("store_level")),
        profile.get("trust_score"),
        profile.get("review_count"),
    )
    try:
        cursor.execute(
            """
            UPDATE search_results sr
            JOIN (
                SELECT id
                FROM search_results
                WHERE product_id = %s
                ORDER BY fetched_at DESC, id DESC
                LIMIT 1
            ) latest ON latest.id = sr.id
            SET
                sr.body_text = COALESCE(%s, sr.body_text),
                sr.body_hash = COALESCE(%s, sr.body_hash),
                sr.body_fetched_at = CASE
                    WHEN %s IS NOT NULL THEN CURRENT_TIMESTAMP
                    ELSE sr.body_fetched_at
                END,
                sr.self_check_json = COALESCE(%s, sr.self_check_json),
                sr.seller_store_seq = COALESCE(%s, sr.seller_store_seq),
                sr.seller_store_name = COALESCE(%s, sr.seller_store_name),
                sr.seller_profile_image_url = COALESCE(%s, sr.seller_profile_image_url),
                sr.seller_store_level = COALESCE(%s, sr.seller_store_level),
                sr.seller_trust_score = COALESCE(%s, sr.seller_trust_score),
                sr.seller_review_count = COALESCE(%s, sr.seller_review_count)
            """,
            (
                values[0], values[1], values[2], values[1], values[3],
                values[4], values[5], values[6], values[7], values[8], values[9],
            ),
        )
        return {"updated": bool(getattr(cursor, "rowcount", 0)), "body_hash": body_hash}
    except Exception as exc:
        if not _is_missing_schema_error(exc):
            raise

    try:
        cursor.execute(
            """
            UPDATE search_results sr
            JOIN (
                SELECT id
                FROM search_results
                WHERE product_id = %s
                ORDER BY fetched_at DESC, id DESC
                LIMIT 1
            ) latest ON latest.id = sr.id
            SET
                sr.body_text = COALESCE(%s, sr.body_text),
                sr.seller_store_seq = COALESCE(%s, sr.seller_store_seq),
                sr.seller_store_name = COALESCE(%s, sr.seller_store_name),
                sr.seller_profile_image_url = COALESCE(%s, sr.seller_profile_image_url),
                sr.seller_store_level = COALESCE(%s, sr.seller_store_level),
                sr.seller_trust_score = COALESCE(%s, sr.seller_trust_score),
                sr.seller_review_count = COALESCE(%s, sr.seller_review_count)
            """,
            (
                values[0], values[1], values[4], values[5], values[6],
                values[7], values[8], values[9],
            ),
        )
        return {
            "updated": bool(getattr(cursor, "rowcount", 0)),
            "body_hash": body_hash,
            "legacy_schema": True,
        }
    except Exception as exc:
        if _is_missing_schema_error(exc):
            return {"updated": False, "reason": "search_results_schema_missing"}
        raise
