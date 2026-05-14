import re


UNKNOWN_COLUMN_ERRNO = 1054


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
            "last_change_reason": _coerce_text(row[7]),
            "last_seen_at": row[8],
            "last_analyzed_at": row[9],
            "seen_count": row[10],
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
        "last_change_reason": None,
        "last_seen_at": legacy_row[4],
        "last_analyzed_at": None,
        "seen_count": 1,
    }


def should_analyze_seen_product(existing, current):
    if not existing:
        return True, "new_product"

    existing_price = _coerce_price(existing.get("last_price_krw"))
    if existing_price is None:
        existing_price = _coerce_price(existing.get("price"))
    current_price = _coerce_price(current.get("price"))
    if existing_price != current_price:
        return True, "price_changed"

    existing_title = _coerce_text(existing.get("last_title")) or _coerce_text(existing.get("title"))
    current_title = _coerce_text(current.get("title"))
    if existing_title != current_title:
        return True, "title_changed"

    current_refresh_key = _coerce_text(current.get("refresh_key"))
    existing_refresh_key = _coerce_text(existing.get("last_refresh_key"))
    if current_refresh_key and current_refresh_key != existing_refresh_key:
        return True, "refresh_key_changed"

    return False, "unchanged"


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
                last_change_reason
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1, %s, %s, %s, %s, %s)
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


def mark_seen_product_analyzed(cursor, product_id):
    normalized_id = _coerce_product_id(product_id)
    if normalized_id is None:
        raise ValueError("product_id/seq가 없습니다.")

    try:
        cursor.execute(
            """
            UPDATE joongna_seen_products
            SET
                last_analyzed_at = CURRENT_TIMESTAMP,
                last_status = %s
            WHERE seq = %s
            """,
            ("analyzed", normalized_id),
        )
        return
    except Exception as exc:
        if not _is_unknown_column_error(exc):
            raise
