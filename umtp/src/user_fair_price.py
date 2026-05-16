from decimal import Decimal

from src.alert_price_direction import (
    DEFAULT_ALERT_PRICE_DIRECTION,
    compute_target_buy_price_krw,
    normalize_alert_price_direction,
)


REQUIRED_SPEC_FIELDS = ("product_type", "chip", "screen_inch", "ram_gb", "ssd_gb")
DEFAULT_SYSTEM_ALERT_DROP_RATE_PERCENT = 20.0


def _normalize_user_id(user_id):
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("user_id는 비어 있을 수 없습니다.")
    return user_id.strip()


def _require_spec_fields(parsed_spec):
    missing_fields = [field for field in REQUIRED_SPEC_FIELDS if parsed_spec.get(field) is None]
    if missing_fields:
        raise ValueError(f"스펙 누락: {', '.join(missing_fields)}")


def _safe_float(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _safe_int(value):
    if value is None:
        return None
    return int(value)


def _normalize_alert_price_row(row):
    if row is None:
        return None

    if isinstance(row, dict):
        fair_price_krw = _safe_int(row.get("fair_price_krw"))
        alert_drop_rate_percent = _safe_float(row.get("alert_drop_rate_percent"))
        target_buy_price_krw = _safe_int(row.get("target_buy_price_krw"))
        alert_price_direction = normalize_alert_price_direction(row.get("alert_price_direction"))
    else:
        row_values = tuple(row)
        fair_price_krw = _safe_int(row_values[0]) if len(row_values) > 0 else None
        alert_drop_rate_percent = _safe_float(row_values[1]) if len(row_values) > 1 else None
        target_buy_price_krw = _safe_int(row_values[2]) if len(row_values) > 2 else None
        raw_direction = row_values[3] if len(row_values) > 3 else DEFAULT_ALERT_PRICE_DIRECTION
        alert_price_direction = normalize_alert_price_direction(raw_direction)

    if target_buy_price_krw is None:
        target_buy_price_krw = compute_target_buy_price_krw(fair_price_krw, alert_drop_rate_percent)

    return {
        "fair_price_krw": fair_price_krw,
        "alert_drop_rate_percent": alert_drop_rate_percent,
        "target_buy_price_krw": target_buy_price_krw,
        "alert_price_direction": alert_price_direction,
    }


def _fetch_user_fair_price_row(cursor, user_id, parsed_spec):
    query_params = (
        user_id,
        parsed_spec["product_type"],
        parsed_spec["chip"],
        parsed_spec["screen_inch"],
        parsed_spec["ram_gb"],
        parsed_spec["ssd_gb"],
    )

    queries = (
        """
        SELECT fair_price_krw, alert_drop_rate_percent, target_buy_price_krw, alert_price_direction
        FROM user_fair_prices
        WHERE user_id = %s
          AND product_type = %s
          AND chip = %s
          AND screen_inch = %s
          AND ram_gb = %s
          AND ssd_gb = %s
          AND enabled = TRUE
        LIMIT 1
        """,
        """
        SELECT fair_price_krw, alert_drop_rate_percent, target_buy_price_krw, alert_price_direction
        FROM user_fair_prices
        WHERE user_id = %s
          AND product_type = %s
          AND chip = %s
          AND screen_inch = %s
          AND ram_gb = %s
          AND ssd_gb = %s
        LIMIT 1
        """,
        """
        SELECT fair_price_krw, alert_drop_rate_percent
        FROM user_fair_prices
        WHERE user_id = %s
          AND product_type = %s
          AND chip = %s
          AND screen_inch = %s
          AND ram_gb = %s
          AND ssd_gb = %s
          AND enabled = TRUE
        LIMIT 1
        """,
        """
        SELECT fair_price_krw, alert_drop_rate_percent
        FROM user_fair_prices
        WHERE user_id = %s
          AND product_type = %s
          AND chip = %s
          AND screen_inch = %s
          AND ram_gb = %s
          AND ssd_gb = %s
        LIMIT 1
        """,
    )

    unknown_column_exc = None
    for query in queries:
        try:
            cursor.execute(query, query_params)
            return cursor.fetchone()
        except Exception as exc:
            if "unknown column" not in str(exc).lower():
                raise
            unknown_column_exc = exc
            continue

    if unknown_column_exc is not None:
        raise unknown_column_exc
    return None


def _has_enabled_user_target(cursor, user_id, parsed_spec):
    try:
        cursor.execute(
            """
            SELECT 1
            FROM user_fair_prices
            WHERE user_id = %s
              AND product_type = %s
              AND chip = %s
              AND screen_inch = %s
              AND ram_gb = %s
              AND ssd_gb = %s
              AND enabled = TRUE
            LIMIT 1
            """,
            (
                user_id,
                parsed_spec["product_type"],
                parsed_spec["chip"],
                parsed_spec["screen_inch"],
                parsed_spec["ram_gb"],
                parsed_spec["ssd_gb"],
            ),
        )
    except Exception as exc:
        if "unknown column" not in str(exc).lower() or "enabled" not in str(exc).lower():
            raise
        cursor.execute(
            """
            SELECT 1
            FROM user_fair_prices
            WHERE user_id = %s
              AND product_type = %s
              AND chip = %s
              AND screen_inch = %s
              AND ram_gb = %s
              AND ssd_gb = %s
            LIMIT 1
            """,
            (
                user_id,
                parsed_spec["product_type"],
                parsed_spec["chip"],
                parsed_spec["screen_inch"],
                parsed_spec["ram_gb"],
                parsed_spec["ssd_gb"],
            ),
        )

    return cursor.fetchone() is not None


def _fetch_system_fair_price_row(cursor, parsed_spec):
    cursor.execute(
        """
        SELECT fair_price_krw
        FROM mac_fair_prices
        WHERE product_type = %s
          AND chip = %s
          AND screen_inch = %s
          AND ram_gb = %s
          AND ssd_gb = %s
        LIMIT 1
        """,
        (
            parsed_spec["product_type"],
            parsed_spec["chip"],
            parsed_spec["screen_inch"],
            parsed_spec["ram_gb"],
            parsed_spec["ssd_gb"],
        ),
    )
    return cursor.fetchone()


def fetch_user_fair_price(cursor, user_id, parsed_spec):
    normalized_user_id = _normalize_user_id(user_id)
    _require_spec_fields(parsed_spec)

    row = _fetch_user_fair_price_row(cursor, normalized_user_id, parsed_spec)
    if not row:
        return None

    normalized_row = _normalize_alert_price_row(row)
    fair_price_krw = normalized_row.get("fair_price_krw")
    alert_drop_rate_percent = normalized_row.get("alert_drop_rate_percent")
    target_buy_price_krw = normalized_row.get("target_buy_price_krw")
    alert_price_direction = normalized_row.get("alert_price_direction")

    return {
        "fair_price_krw": fair_price_krw,
        "alert_drop_rate_percent": alert_drop_rate_percent,
        "target_buy_price_krw": target_buy_price_krw,
        "alert_price_direction": alert_price_direction,
        "source": "user_fair_prices",
    }


def is_user_fair_price_target_enabled(cursor, user_id, parsed_spec):
    normalized_user_id = _normalize_user_id(user_id)
    _require_spec_fields(parsed_spec)
    return _has_enabled_user_target(cursor, normalized_user_id, parsed_spec)


def resolve_fair_price_for_user(cursor, user_id, parsed_spec):
    normalized_user_id = _normalize_user_id(user_id)
    _require_spec_fields(parsed_spec)

    if not _has_enabled_user_target(cursor, normalized_user_id, parsed_spec):
        return None

    user_row = _fetch_user_fair_price_row(cursor, normalized_user_id, parsed_spec)
    if user_row:
        normalized_row = _normalize_alert_price_row(user_row)
        return {
            "fair_price_krw": normalized_row.get("fair_price_krw"),
            "alert_drop_rate_percent": normalized_row.get("alert_drop_rate_percent"),
            "target_buy_price_krw": normalized_row.get("target_buy_price_krw"),
            "alert_price_direction": normalized_row.get("alert_price_direction"),
            "source": "user_fair_prices",
        }

    system_row = _fetch_system_fair_price_row(cursor, parsed_spec)
    if system_row:
        fair_price_krw = int(system_row[0])
        alert_drop_rate_percent = DEFAULT_SYSTEM_ALERT_DROP_RATE_PERCENT
        return {
            "fair_price_krw": fair_price_krw,
            "alert_drop_rate_percent": alert_drop_rate_percent,
            "target_buy_price_krw": compute_target_buy_price_krw(
                fair_price_krw,
                alert_drop_rate_percent,
            ),
            "alert_price_direction": DEFAULT_ALERT_PRICE_DIRECTION,
            "source": "mac_fair_prices",
        }

    return None
